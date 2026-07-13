from dotenv import load_dotenv
load_dotenv()

from ingestion.embeddings import LangfuseEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_core.documents import Document
from qdrant_client import models

from ingestion.call_graph import build_call_graph
from ingestion.repo_source import resolve_repo
from ingestion.index import sync_index
from retrieval.graph_expand import expand_with_graph

QDRANT_URL = 'http://localhost:6333'
COLLECTION_NAME = 'codebase'

# Scoring weights for the final ranking
W_SEMANTIC = 0.6
W_GRAPH = 0.3
W_IMPORTANCE = 0.1

# How many functions to feed forward as context
MAX_CONTEXT_FUNCS = 6


def _uid(doc):
    return doc.metadata["uid"]


def _normalize(scores):
    """Min-max normalize a {key: value} dict into [0, 1]."""
    if not scores:
        return {}
    lo = min(scores.values())
    hi = max(scores.values())
    if hi == lo:
        return {k: 1.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


def _fetch_docs_by_uids(vector_db, uids):
    """Look up stored code/summary for a set of uids straight from Qdrant.

    This is what lets graph-expanded functions (which weren't in the top-k
    semantic hits) actually contribute their code to the context, instead of
    being passed forward as bare names with no content.
    """
    uids = [u for u in uids]
    if not uids:
        return {}

    points, _ = vector_db.client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=models.Filter(
            must=[models.FieldCondition(
                key="metadata.uid",
                match=models.MatchAny(any=uids),
            )]
        ),
        limit=len(uids),
        with_payload=True,
    )

    docs = {}
    for p in points:
        metadata = p.payload.get("metadata", {})
        uid = metadata.get("uid")
        if uid is None:
            continue
        docs[uid] = Document(
            page_content=p.payload.get("page_content", ""),
            metadata=metadata,
        )
    return docs


def search_code(user_query, repo, token=None):
    # Reuse the already-cloned/local copy (don't re-pull on every query).
    repo_path = resolve_repo(repo, token=token, update=False)

    # Reconcile the index with the current code on disk before answering, so
    # edits (the edit agent, manual, git pull) are reflected. Cheap when nothing
    # changed; only re-summarizes the functions that actually changed.
    sync_index(repo_path)

    embedding_model = LangfuseEmbeddings()

    vector_db = QdrantVectorStore.from_existing_collection(
        url=QDRANT_URL,
        collection_name=COLLECTION_NAME,
        embedding=embedding_model,
    )

    results_with_scores = vector_db.similarity_search_with_score(
        query=user_query, k=5
    )
    results = [r for r, _ in results_with_scores]

    # Semantic score: langchain-qdrant returns a cosine similarity
    # (higher = more relevant), so use it directly and min-max normalize
    # so it shares the [0, 1] scale with the other signals.
    semantic_scores = _normalize({
        _uid(r): score for r, score in results_with_scores
    })

    call_graph, reverse_graph = build_call_graph(repo_path)
    expanded = expand_with_graph(results_with_scores, call_graph, reverse_graph)

    # graph score (shallower depth = more relevant)
    graph_scores = {uid: 1 / (depth + 1) for uid, depth in expanded.items()}

    # importance score (how many functions call this one), normalized
    importance_scores = _normalize({
        uid: len(reverse_graph.get(uid, [])) for uid in expanded
    })

    # combine signals over every candidate uid
    all_uids = set(semantic_scores) | set(expanded)
    scores = {}
    for uid in all_uids:
        scores[uid] = (
            semantic_scores.get(uid, 0) * W_SEMANTIC +
            graph_scores.get(uid, 0) * W_GRAPH +
            importance_scores.get(uid, 0) * W_IMPORTANCE
        )

    ranked_uids = sorted(scores, key=scores.get, reverse=True)
    top_uids = ranked_uids[:MAX_CONTEXT_FUNCS]

    # Build a uid -> Document map. Start with the semantic hits (which
    # already carry content), then fetch any remaining top uids from Qdrant.
    doc_map = {_uid(r): r for r in results}
    missing = [uid for uid in top_uids if uid not in doc_map]
    doc_map.update(_fetch_docs_by_uids(vector_db, missing))

    # Final ordered, de-duplicated results with real content only.
    final_results = []
    for uid in top_uids:
        doc = doc_map.get(uid)
        if doc is not None:
            final_results.append(doc)

    return final_results, set(top_uids)
