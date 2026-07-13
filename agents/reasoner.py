from dotenv import load_dotenv
load_dotenv()

from langfuse.openai import OpenAI  # drop-in wrapper: records each call as a Langfuse generation
client = OpenAI()


def _system_prompt(query, compressed_context, expanded_funcs, memory_context):
    return f'''
     You are an expert software engineer.

     You are given:
     1. Compressed summaries of relevant functions
     2. Function call relationships

     Answer the user's question using only the codebase context below.

     Previous conversation:
     {memory_context}

     Relevant functions and roles:
     {compressed_context}

     Related functions (call graph):
     {expanded_funcs}

     Instructions:
     - Explain how things work step-by-step
     - Connect functions logically
     - Identify possible issues
     - Do NOT infer personal information from code
     - Memory context is only for conversational continuity, not identity inference
     - Be precise
     - Avoid generic explanations
     - Focus on THIS codebase only
     - Use function names explicitly
    '''


def _messages(query, compressed_context, expanded_funcs, memory_context):
    return [
        {'role': 'system',
         'content': _system_prompt(query, compressed_context, expanded_funcs, memory_context)},
        {'role': 'user', 'content': query},
    ]


# Generate final answer using LLM (single shot)
def generate_answer(query, compressed_context, expanded_funcs, memory_context):
    response = client.chat.completions.create(
        model='gpt-4.1-mini',
        messages=_messages(query, compressed_context, expanded_funcs, memory_context),
    )
    return response.choices[0].message.content


# Stream the answer token-by-token (yields text deltas).
def stream_answer(query, compressed_context, expanded_funcs, memory_context):
    stream = client.chat.completions.create(
        model='gpt-4.1-mini',
        messages=_messages(query, compressed_context, expanded_funcs, memory_context),
        stream=True,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
