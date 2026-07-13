from ingestion.index import index_repo
from retrieval.query import search_code
from agents.context_extender import build_compressed_context
from agents.reasoner import generate_answer
from agents.debugger import debugger_agent
from memory.mem0 import init_memory, get_mem_context, save_memory
from router import route_query

mem_client = init_memory()

repo_path = input('Enter repo path: ')
index_repo(repo_path)

while True:
    query = input('Ask question: ')

    mem_context = get_mem_context(mem_client, query)
    
    route = route_query(query)
    
    # search_code already returns the curated, ranked functions.
    results, expanded_funcs = search_code(query, repo_path)

    compressed_context = build_compressed_context(results)

    if route == "debugger":
        answer = debugger_agent(
        query,
        compressed_context
    )
    else:
        answer = generate_answer(
         query,
        compressed_context,
        expanded_funcs,
        mem_context
        )

    print(answer)
    
    save_memory(mem_client, query, answer)