import streamlit as st

from memory.mem0 import init_memory, get_mem_context, save_memory
from retrieval.query import search_code
from agents.context_extender import build_compressed_context
from agents.reasoner import generate_answer
from agents.debugger import debugger_agent
from ingestion.index import index_repo
from router import route_query

mem_client = init_memory()

# ---------------- UI CONFIG ----------------
st.set_page_config(page_title="CodeComp", layout="wide")
st.title("CodeComp")

# ---------------- REPO INPUT ----------------
repo_path = st.text_input(
    "Repository Path",
    value=".",
    help="Use '.' for current directory or provide full path"
)

col1, col2 = st.columns([1, 1])

with col1:
    if st.button("Index Repository"):
        with st.spinner("Indexing repository..."):
            try:
                index_repo(repo_path)
                st.success("Indexing completed")
            except Exception as e:
                st.error(f"Indexing failed: {str(e)}")

st.divider()

# ---------------- QUERY ----------------
query = st.text_input("Ask a question about the codebase")

if st.button("Run") and query:
    with st.spinner("Processing..."):
        try:
            # -------- MEMORY --------
            memory_context = get_mem_context(mem_client, query)

            # -------- ROUTING --------
            route = route_query(query)

            # -------- RETRIEVAL --------
            results, expanded = search_code(query, repo_path)

            filtered_results = [
                r for r in results
                if r.metadata["function"] in expanded
            ]

            compressed_context = build_compressed_context(filtered_results)

            # -------- AGENT EXECUTION --------
            if route == "debugger":
                answer = debugger_agent(
                    query,
                    compressed_context
                )
            else:
                answer = generate_answer(
                    query,
                    compressed_context,
                    expanded,
                    memory_context
                )

            # -------- SAVE MEMORY --------
            save_memory(mem_client, query, answer)

            # -------- OUTPUT --------
            st.subheader("Answer")
            st.write(answer)

            # -------- CONTEXT INSPECTION --------
            with st.expander("Context Used"):
                st.text(compressed_context[:2000])

            # -------- FUNCTION INSPECTION --------
            st.subheader("Relevant Functions")

            for r in filtered_results:
                func_name = r.metadata.get("function", "unknown")
                file_name = r.metadata.get("file", "unknown")

                with st.expander(f"{func_name} ({file_name})"):
                    st.code(r.page_content, language="python")

        except Exception as e:
            st.error(f"Error: {str(e)}")