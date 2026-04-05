# CodeComp (v1)

> Ask questions about a codebase. Get answers grounded in the actual code.

---

##  What is CodeComp?

CodeComp is a system that lets you interact with a codebase using natural language.

Instead of:
- opening files  
- tracing function calls  
- building mental maps  

You can:
> provide a repository → ask a question → get a structured explanation

---

##  What it does

- Extracts function-level chunks using AST  
- Builds relationships between functions (call graph)  
- Retrieves relevant code using embeddings  
- Expands context using graph traversal  
- Generates answers using an LLM  
- Maintains conversational memory across queries  

---

##  System Architecture

    Codebase → AST Chunking → Summaries → Embeddings (Qdrant)
                                          ↓
    User Query → Retrieval → Graph Expansion → Context Compression
                                                  ↓
                                          LLM Reasoning
                                                  ↓
                                              Answer

---

##  Example Queries

- "How does this feature work end-to-end?"  
- "Which functions are involved in this flow?"  
- "Where could this be breaking?"  
- "What calls this function and why?"  

---

##  Setup

### 1. Clone the repo

    git clone https://github.com/yashwork-byte/CompCode
    cd CompCode

### 2. Install dependencies

    pip install -r requirements.txt

### 3. Start Qdrant (Docker)

    docker run -p 6333:6333 qdrant/qdrant

### 4. Setup environment variables

Create a `.env` file in the root:

    OPENAI_API_KEY=your_key_here

---

##  Run

### CLI

    python main.py

### Streamlit UI

    streamlit run app.py

---

##  Limitations

- Python-only support  
- Function-level granularity  
- Heuristic ranking  
- Not optimized for large or multi-language repos  
- Works best on local repositories  

---

##  Key Design Ideas

- Structure first (AST), semantics later (LLM)  
- Graph-based context over flat retrieval  
- Precompute expensive steps (summaries)  
- Not all context should be treated equally (memory vs code)  

---

##  Future Work

- Debugging agent with tool calling  
- Better ranking strategies  
- Multi-language support  
- Scalable background processing (RQ)  
- Improved memory isolation  

---

##  Open to Feedback

If you’ve worked on:
- code search  
- developer tools  
- LLM systems  

I’d really value your feedback.

---

##  Article

Read the full breakdown here:  
 https://medium.com/@tarunyash01/v1-codecomp-building-a-system-to-reason-over-a-codebase-0267ca507b9d

---

##  Note

This is v1.

It works well enough to be useful.  
And imperfect enough to keep improving.