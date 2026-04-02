import streamlit as st

from memory.mem0 import init_memory, get_mem_context, save_memory
from retrieval.query import search_code
from agents.context_extender import build_compressed_context
from agents.reasoner import generate_answer
from ingestion.index import index_repo

mem_client = init_memory()

st.set_page_config(page_title="CodeComp")
st.title("CodeComp")

repo_path = st.text_input(
    "Enter repo path",
    value=".",
    help="Use '.' for current directory or full path"
)

if st.button(" Index Repo"):
    with st.spinner("Indexing repository..."):
        try:
            index_repo(repo_path)
            st.success(" Indexing completed")
        except Exception as e:
            st.error(f"Indexing failed: {str(e)}")

st.divider()

query = st.text_input("Ask about the codebase")

if st.button(" Run") and query:
    with st.spinner("Thinking..."):
        try:
            memory_context = get_mem_context(mem_client, query)

            results, expanded = search_code(query, repo_path)

            compressed_context = build_compressed_context(results)

            answer = generate_answer(
                query,
                compressed_context,
                expanded,
                memory_context
            )

            save_memory(mem_client, query, answer)

            st.subheader("Answer")
            st.write(answer)

            st.subheader(" Relevant Functions")
            for r in results:
                func_name = r.metadata.get("function", "unknown")
                file_name = r.metadata.get("file", "unknown")

                with st.expander(f"{func_name} ({file_name})"):
                    st.code(r.page_content, language="python")

        except Exception as e:
            st.error(f"Error: {str(e)}")