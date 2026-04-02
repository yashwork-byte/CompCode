from ingestion.index import index_repo
from retrieval.query import search_code
from agents.context_extender import build_compressed_context
from agents.reasoner import generate_answer
from memory.mem0 import init_memory, get_mem_context, save_memory

mem_client = init_memory()

repo_path = input('Enter repo path: ')
index_repo(repo_path)

while True:
    query = input('Ask question: ')

    mem_context = get_mem_context(mem_client, query)
    
    results, expanded_funcs = search_code(query, repo_path)

    filtered_results = [
    r for r in results
    if r.metadata["function"] in expanded_funcs
    ]   

    compressed_context = build_compressed_context(filtered_results)

    answer = generate_answer(
     query,
     compressed_context,
     expanded_funcs,
     mem_context
    )

    print(answer)
    
    save_memory(mem_client, query, answer)