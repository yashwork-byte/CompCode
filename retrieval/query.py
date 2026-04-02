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
    
    results = vector_db.similarity_search(query = user_query, k = 5)
    
    call_graph, reverse_graph = build_call_graph(repo_path)
    expanded_funcs = expand_with_graph(results, call_graph, reverse_graph)

    scores = {}

    for r in results:
     func = r.metadata["function"]
     scores[func] = 3

    for func in expanded_funcs:
        if func not in scores:
            scores[func] = 3

    ranked_funcs = sorted(scores, key=scores.get, reverse=True)

    expanded_funcs = set(ranked_funcs[:6])
    # print("\nInitial functions:")
    # for r in results:
    #   print(r.metadata["function"])

    # print("\nExpanded functions from graph:")
    # print(expanded_funcs)
    
    expanded_results = []

    for func in expanded_funcs:
     new_docs = vector_db.similarity_search(func, k=1)
     expanded_results.extend(new_docs)

    all_results = results + expanded_results

    seen = set()
    final_results = []

    for r in all_results:
     func = r.metadata["function"]
     if func not in seen:
        seen.add(func)
        final_results.append(r)
                
    # for i, r in enumerate(final_results):
    #     print(f"\n--- Result {i+1} ---")
    #     print(f"File: {r.metadata['file']}")
    #     print(f"Function: {r.metadata['function']}")
    #     print(r.page_content[:300])

    return final_results, expanded_funcs