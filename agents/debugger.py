from dotenv import load_dotenv
load_dotenv()

import os
import json
from openai import OpenAI
client = OpenAI()

def run_command(cmd: str):
    result = os.system(cmd)
    return result

history = []

def debugger_agent(query, context, max_steps = 5):
    SYSTEM_PROMPT = f'''
        You are a code debugging agent.

        You have access to:
        - run_command(cmd: str)

        You must respond in JSON

        FORMAT:

        {{
            'thought': 'What are you thinking?',
            'action': 'run_command or DONE',
            'cmd': 'shell command if action is run_command',
            'final_answer': 'only if DONE'
        }}

        STRICT RULES:
        1. If the query involves ANY file operation (create, delete, modify, write):
        → You MUST call run_command
        → You are NOT allowed to assume the result

        2. NEVER say a file does not exist WITHOUT running a command

        3. ALWAYS attempt the command first, then observe result

        4. DO NOT return explanations for action queries

        5. Only use "DONE" after executing the required commands
        
    '''
    
    for step in range(max_steps):
        messages = [
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': f'Query : {query}\n Context :\n {context}'}
            ]
        for h in history:
            messages.append({'role': 'assistant', 'content': h})
            
        response = client.chat.completions.create(
            model = 'gpt-4.1-mini',
            messages = messages
        )
        
        output = response.choices[0].message.content
        
        try:
            data = json.loads(output)
        except:
            return output 

        action = data.get("action")
        
        if action == "DONE":
            return data.get("final_answer", "Done")

        if action == "run_command":
            cmd = data.get("cmd")
            result = run_command(cmd)

            history.append(output)
            history.append(f"Observation: {result}")

        else:
            return "Invalid action"

    return "Max steps reached"
