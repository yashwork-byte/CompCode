from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
import json

client = OpenAI()

def judge_explanation(query, answer, context):
    prompt = f'''
    You are evaluating a system that answers questions about a codebase.
    
    Query:
    {query}
    
    Answer:
    {answer}
    
    Context:
    {context}
    
    Evaluate:
    
    1. Relevance (0-5)
    2. Groundedness (0-5)
    3. Correctness (0-5)
    
    Return STRICT JSON:
    
    {{
        "relevance" : int,
        "groundedness" : int,
        "correctness" : int,
        "reason" : "short explanation"
    }}
    '''
    
    response = client.chat.completions.create(
        model = 'gpt-4.1-mini',
        messages = [
            {'role': 'user', 'content': prompt}
        ],
        response_format = {"type": "json_object"}
    )

    try:
        return json.loads(response.choices[0].message.content)
    except (json.JSONDecodeError, TypeError):
        return {"relevance": 0, "groundedness": 0, "correctness": 0,
                "reason": "judge returned unparseable output"}