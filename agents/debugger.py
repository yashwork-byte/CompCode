from dotenv import load_dotenv
load_dotenv()

import os
import json
from openai import OpenAI
client = OpenAI()

def run_command(cmd: str):
    result = os.system(cmd)
    return result


def debugger_agent(query, context):
    SYSTEM_PROMPT = f'''
        You are a code debugging agent.

        You have access to:
        - run_command(cmd: str)

        STRICT RULES:

        1. If the user asks to:
        - create file
        - modify file
        - write code
        - update code

        → You MUST use run_command

        2. DO NOT explain what you will do
        3. DO NOT return code unless explicitly asked ONLY for explanation
        4. ALWAYS respond in JSON

        FORMAT:

        If action required:
        {{
        "action": "run_command",
        "cmd": "your shell command"
        }}

        If no action required:
        {{
        "action": "none",
        "response": "your explanation"
        }}

        Context:
        {context}
    '''
    
    response = client.chat.completions.create(
        model = 'gpt-4.1-mini',
        messages = [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': query}
        ]
    )
    
    output = response.choices[0].message.content
    
    try:
        data = json.loads(output)
    except:
        return output 

    if data.get("action") == "run_command":
        cmd = data.get("cmd")
        result = run_command(cmd)
        return f"Executed: {cmd}\nOutput:\n{result}"

    return data.get("response", output)
