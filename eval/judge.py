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
        ]
    )
    
    return json.loads(response.choices[0].message.content)
    
def judge_debugger(output, expected_action):
    if expected_action == "run_command":
        success_signals = [
            "created",
            "deleted",
            "written",
            "updated",
            "file",
        ]

        out = output.lower()

        if any(word in out for word in success_signals):
            return {"score": 1, "reason": "Action likely executed"}
        else:
            return {"score": 0, "reason": "No action detected"}

    return {"score": 0, "reason": "Unknown expected action"}