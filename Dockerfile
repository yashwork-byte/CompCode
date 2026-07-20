# Backend image for the CodeComp FastAPI service (QA mode).
# Editing is intentionally not available here — it needs a local checkout with
# deps installed (see README). This image serves QA over local/GitHub repos.
FROM python:3.12-slim

# git: GitPython shells out to it to clone GitHub repos.
# build-essential: some deps (tree-sitter grammars, etc.) may compile on install.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first so this layer caches across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloned repos land under $HOME/.codecomp/repos (ephemeral on most hosts).
ENV HOME=/root

# Hosts inject the port via $PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]
