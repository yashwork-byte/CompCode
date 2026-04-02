from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
client = OpenAI()

def summarize_chunks(chunk):
    prompt = f'''
        You are summarizing a function for comprehension purposes.
        
        Focus on 
        - what the function does
        - key logic
        - important dependencies

        Function:
        Name: {chunk.metadata['function']}
        File: {chunk.metadata['file']}

        Code:
        {chunk.page_content}
    '''
    
    response = client.chat.completions.create(
        model = 'gpt-4.1-mini',
        messages = [
            {'role': 'user', 'content': prompt}
        ]
    )
    
    return response.choices[0].message.content

def build_compressed_context(chunks):
    summaries = []
    for chunk in chunks:
        summary = summarize_chunks(chunk)
        summaries.append(
            f"{chunk.metadata['function']} : {summary}"
        )
    return '\n'.join(summaries)