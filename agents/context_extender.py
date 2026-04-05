from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
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