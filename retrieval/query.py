from dotenv import load_dotenv
load_dotenv()

from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from ingestion.call_graph import build_call_graph
from retrieval.graph_expand import expand_with_graph

def search_code(user_query, repo_path):
    embedding_model = OpenAIEmbeddings(
        model = 'text-embedding-3-small'
    )
    
    vector_db = QdrantVectorStore.from_existing_collection(
        url = 'http://localhost:6333',
        collection_name = 'codebase',
        embedding = embedding_model
    )
    
    results_with_scores = vector_db.similarity_search_with_score(query = user_query, k = 5)
    results = [r for r, _ in results_with_scores]
    
    # Normalize semantic scores
    semantic_scores = {}

    for r, score in results_with_scores:
     func = r.metadata["function"]
     semantic_scores[func] = 1 - score
        
    call_graph, reverse_graph = build_call_graph(repo_path)
    expanded_funcs = expand_with_graph(results_with_scores, call_graph, reverse_graph)

    func_map = {r.metadata["function"]: r for r in results}
    
    # graph score (based on depth)
    graph_scores = {}
    for func, depth in expanded_funcs.items():
      graph_scores[func] = 1 / (depth + 1)

    # importance score
    importance_scores = {}
    for func in expanded_funcs:
     importance_scores[func] = len(reverse_graph.get(func, []))

    # normalize importance
    max_importance = max(importance_scores.values(), default=0)
    if max_importance > 0:
     for func in importance_scores:
          importance_scores[func] /= max_importance
    else:
       for func in importance_scores:
            importance_scores[func] = 0

    # combine scores
    scores = {}

    all_funcs = set(list(semantic_scores.keys()) + list(expanded_funcs.keys()))

    for func in all_funcs:
      scores[func] = (
            semantic_scores.get(func, 0) * 0.6 +
            graph_scores.get(func, 0) * 0.3 +
            importance_scores.get(func, 0) * 0.1
        )


    ranked_funcs = sorted(scores, key=scores.get, reverse=True)

    expanded_funcs = set(ranked_funcs[:6])
    
    expanded_results = []

    for func in expanded_funcs:
        if func in func_map:
            expanded_results.append(func_map[func])

    all_results = results + expanded_results

    seen = set()
    final_results = []

    for r in all_results:
     func = r.metadata["function"]
     if func not in seen:
        seen.add(func)
        final_results.append(r)
                
    return final_results, expanded_funcs