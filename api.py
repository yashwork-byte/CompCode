"""FastAPI backend for CodeComp.

The request pipeline is a LangGraph workflow (see graph/build.py):

    route -> retrieve -> {qa answer | edit workflow with a human review gate}

Run with:

    uvicorn api:app --reload --port 8000
"""

from dotenv import load_dotenv
load_dotenv()

import json
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from langgraph.types import Command

from langfuse import get_client, propagate_attributes
from langfuse.langchain import CallbackHandler

from ingestion.index import index_repo
from memory.mem0 import init_memory, get_mem_context, save_memory
from graph.build import build_graph

app = FastAPI(title="CodeComp API", version="3.0")

# Allow the local Next.js dev server to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compile the workflow once (MemorySaver persists paused edit reviews so a
# later /resume can continue them within this process).
GRAPH = build_graph()

# Observability: the LangChain CallbackHandler traces each graph run as a
# Langfuse trace with a span per node. Raw OpenAI calls inside the nodes are
# traced separately by the langfuse.openai wrapper and auto-nest under these
# spans. Reads LANGFUSE_* from the environment; disabled if keys are absent.
langfuse = get_client()
langfuse_handler = CallbackHandler()

# Memory is optional: if it can't initialise (e.g. Qdrant/key missing) the
# API still serves queries, just without conversational continuity.
try:
    mem_client = init_memory()
except Exception as e:  # noqa: BLE001
    print(f"[warn] memory disabled: {e}")
    mem_client = None


class IndexRequest(BaseModel):
    repo: str
    token: str | None = None


class QueryRequest(BaseModel):
    repo: str
    query: str
    token: str | None = None
    thread_id: str | None = None


class ResumeRequest(BaseModel):
    thread_id: str
    decision: str            # "approve" | "reject"
    feedback: str | None = None


@app.get("/health")
def health():
    return {"status": "ok", "memory": mem_client is not None}


@app.post("/index")
def index(req: IndexRequest):
    try:
        result = index_repo(req.repo, token=req.token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e}")
    return {
        "repo": req.repo,
        "num_functions": result["num_functions"],
        "languages": result["languages"],
    }


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _drive(payload, thread_id: str):
    """Stream a graph run (initial invoke or a resume) as SSE.

    Emits: `meta` (route + functions) -> `token` deltas -> then either
    `interrupt` (edit awaiting review, carries the diff) or `done`.
    """
    cfg = _config(thread_id)
    # Trace this run in Langfuse; the thread_id doubles as the session so all
    # turns of one conversation (and its /resume) group together.
    stream_cfg = {**cfg, "callbacks": [langfuse_handler]}
    interrupted = False
    try:
        with propagate_attributes(session_id=thread_id):
            for mode, chunk in GRAPH.stream(payload, stream_cfg, stream_mode=["custom", "updates"]):
                if mode == "custom":
                    kind = chunk.get("type")
                    if kind == "meta":
                        yield _sse("meta", chunk["data"])
                    elif kind == "token":
                        yield _sse("token", {"text": chunk["text"]})
                elif mode == "updates" and "__interrupt__" in chunk:
                    interrupt_obj = chunk["__interrupt__"][0]
                    interrupted = True
                    yield _sse("interrupt", {"thread_id": thread_id, **interrupt_obj.value})

        if not interrupted:
            final = GRAPH.get_state(cfg).values
            if mem_client and final.get("query") and final.get("answer"):
                try:
                    save_memory(mem_client, final["query"], final["answer"])
                except Exception:  # noqa: BLE001
                    pass
            yield _sse("done", {"status": final.get("status", ""),
                                "answer": final.get("answer", "")})
    except ValueError as e:
        yield _sse("error", {"detail": str(e)})
    except Exception as e:  # noqa: BLE001
        yield _sse("error", {"detail": f"Request failed: {e}"})


@app.post("/query/stream")
def query_stream(req: QueryRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query is empty")
    thread_id = req.thread_id or uuid.uuid4().hex
    mem_context = get_mem_context(mem_client, req.query) if mem_client else ""
    inputs = {
        "query": req.query,
        "repo": req.repo,
        "token": req.token,
        "memory_ctx": mem_context,
    }
    return StreamingResponse(_drive(inputs, thread_id), media_type="text/event-stream")


@app.post("/resume")
def resume(req: ResumeRequest):
    """Resume a paused edit review with the human's decision."""
    cmd = Command(resume={"decision": req.decision, "feedback": req.feedback or ""})
    return StreamingResponse(_drive(cmd, req.thread_id), media_type="text/event-stream")
