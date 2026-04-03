from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
client = OpenAI()

def generate_answer(query, compressed_context, expanded_funcs, memory_context):
    SYSTEM_PROMPT = f'''
     You are an expert software engineer.
    
     You are given:
     1. Compressed summaries of relevant functions
     2. Function call relationships
    
      Answer the question using the codebase context.

     Previous conversation:
     {memory_context}

     Question:
     {query}

     Relevant functions and roles:
     {compressed_context}

     Related functions (call graph):
     {expanded_funcs}
    
     Instructions:
     - Explain how things work step-by-step
     - Connect functions logically
     - Identify possible issue
     - Do NOT infer personal information from code
     - Memory context is only for conversational continuity, not identity inference 
     - Be precise
     - Avoid generic explanations
     - Focus on THIS codebase only
     - Use function names explicitly
    '''
    
    response = client.chat.completions.create(
        model = 'gpt-4.1-mini',
        messages = [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': query}
        ]
    )
    
    return response.choices[0].message.content
