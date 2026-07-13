from dotenv import load_dotenv
load_dotenv()

import uuid
import hashlib

from ingestion.code_ingest import extract_chunks
from ingestion.repo_source import resolve_repo
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI
client = OpenAI()

QDRANT_URL = 'http://localhost:6333'
COLLECTION_NAME = 'codebase'

# Stable namespace so a given uid always maps to the same Qdrant point id.
_UID_NAMESPACE = uuid.UUID('00000000-0000-0000-0000-00000000c0de')


def _point_id(uid):
    """Deterministic point id for a function uid (enables upsert, not append)."""
    return str(uuid.uuid5(_UID_NAMESPACE, uid))


def _code_hash(code):
    """Content hash of a function body, used to detect changes on re-sync."""
    return hashlib.sha1(code.encode('utf-8', 'replace')).hexdigest()


def _embedding_model():
    return OpenAIEmbeddings(model='text-embedding-3-small')


# Generate natural language summary for a function
def generate_summary(chunk):
    prompt = f'''
    You are summarizing a function for comprehension purposes.

        Focus on
        - what the function does
        - key logic
        - important dependencies

    Function Name : {chunk['function']}
    Code : {chunk['code']}
    '''

    response = client.chat.completions.create(
        model = 'gpt-4.1-mini',
        messages = [
            {'role': 'user', 'content': prompt}
        ]
    )

    return response.choices[0].message.content

# Process chunk into (id, text, metadata) for the vector DB.
# Returns None if summarization fails, so one bad chunk doesn't abort the run.
def process_chunk(chunk):
    try:
        summary = generate_summary(chunk)
    except Exception as e:
        print(f"Summary failed for {chunk['uid']}: {e}")
        return None

    text = f"""
    Function: {chunk['function']}
    Summary: {summary}
    """

    metadata = {
        "uid": chunk["uid"],
        "function": chunk["function"],
        "file": chunk["file"],
        "language": chunk.get("language", ""),
        "code": chunk["code"],
        "code_hash": _code_hash(chunk["code"]),
        "summary": summary
    }

    return _point_id(chunk["uid"]), text, metadata


def _summarize_chunks(chunks):
    """Summarize + package a list of chunks in parallel. Returns (ids, texts, metadatas)."""
    ids, texts, metadatas = [], [], []
    with ThreadPoolExecutor(max_workers=5) as executor:
        for processed in executor.map(process_chunk, chunks):
            if processed is None:
                continue
            pid, text, metadata = processed
            ids.append(pid)
            texts.append(text)
            metadatas.append(metadata)
    return ids, texts, metadatas


# Index entire repository into vector database (full rebuild).
# `repo` may be a local path or a GitHub/remote URL. Returns the resolved
# local path so callers (CLI/API) can reuse it for querying.
def index_repo(repo, token=None):
    repo_path = resolve_repo(repo, token=token, update=True)
    chunks = extract_chunks(repo_path)

    ids, texts, metadatas = _summarize_chunks(chunks)

    if not texts:
        print('Nothing to index')
        return {"local_path": repo_path, "num_functions": 0, "languages": []}

    # Re-indexing is a full rebuild: drop the old collection so stale points
    # (deleted functions, or an older metadata schema) can't linger. Combined
    # with deterministic ids below, this guarantees no duplicate accumulation.
    try:
        QdrantClient(url=QDRANT_URL).delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    QdrantVectorStore.from_texts(
        texts = texts,
        metadatas = metadatas,
        ids = ids,
        embedding = _embedding_model(),
        url = QDRANT_URL,
        collection_name = COLLECTION_NAME
    )

    languages = sorted({m.get("language", "") for m in metadatas if m.get("language")})
    print(f'Indexing completed ({len(texts)} functions)')
    return {
        "local_path": repo_path,
        "num_functions": len(texts),
        "languages": languages,
    }


def _stored_hashes(qdrant):
    """Map uid -> code_hash for everything currently in the collection."""
    stored = {}
    offset = None
    while True:
        points, offset = qdrant.scroll(
            collection_name=COLLECTION_NAME,
            with_payload=True,
            with_vectors=False,
            limit=256,
            offset=offset,
        )
        for p in points:
            md = p.payload.get("metadata", {})
            uid = md.get("uid")
            if uid is not None:
                stored[uid] = md.get("code_hash")
        if offset is None:
            break
    return stored


# Incrementally reconcile the index with the current state of the repo on disk.
#
# This is what keeps answers correct after the code changes (the edit agent,
# manual edits, git pull). Only changed/new functions are re-summarized (LLM
# cost proportional to the diff); deleted functions are removed. If nothing
# changed it's just a parse + a scroll — no LLM calls.
def sync_index(repo_path):
    qdrant = QdrantClient(url=QDRANT_URL)

    # Collection missing entirely -> do a full index.
    try:
        exists = qdrant.collection_exists(COLLECTION_NAME)
    except Exception:
        exists = False
    if not exists:
        return index_repo(repo_path)

    # Current state from disk (parsing only, no LLM).
    chunks = extract_chunks(repo_path)
    current = {c["uid"]: c for c in chunks}
    current_hashes = {uid: _code_hash(c["code"]) for uid, c in current.items()}

    stored = _stored_hashes(qdrant)

    changed = [current[uid] for uid, h in current_hashes.items()
               if stored.get(uid) != h]
    removed_uids = [uid for uid in stored if uid not in current]

    if removed_uids:
        qdrant.delete(
            collection_name=COLLECTION_NAME,
            points_selector=models.PointIdsList(
                points=[_point_id(uid) for uid in removed_uids]
            ),
        )

    if changed:
        ids, texts, metadatas = _summarize_chunks(changed)
        if texts:
            store = QdrantVectorStore.from_existing_collection(
                url=QDRANT_URL,
                collection_name=COLLECTION_NAME,
                embedding=_embedding_model(),
            )
            store.add_texts(texts=texts, metadatas=metadatas, ids=ids)

    if changed or removed_uids:
        print(f"Index synced (+{len(changed)} updated, -{len(removed_uids)} removed)")

    return {
        "updated": len(changed),
        "removed": len(removed_uids),
        "total": len(current),
    }
