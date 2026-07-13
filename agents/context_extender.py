from dotenv import load_dotenv
load_dotenv()

from langfuse.openai import OpenAI  # drop-in wrapper: records each call as a Langfuse generation
client = OpenAI()

# Build compressed context from retrieved chunks
def build_compressed_context(chunks):
    context_parts = []

    for chunk in chunks:
        func = chunk.metadata.get("function")
        summary = chunk.metadata.get("summary")

        if not summary:
            summary = chunk.page_content[:200]

        context_parts.append(f"{func}: {summary}")

    return "\n".join(context_parts)