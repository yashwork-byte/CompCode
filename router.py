from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
client = OpenAI()

def route_query(user_query):
    SYSTEM_PROMPT = f'''
            You are now a routing agent. 
            
            Your job is to classify user_query into one of two categories.
            
            1. 'codebase' -> user wants explanation/understanding
            2. 'debugger' -> user wants to modify, fix, write or execute code
            
            Rules:
            - Return only one word: 'codebase' or 'debugger'
            - No explanation
            
            Example:
            
            Q. What is the significance of router.py file?
            A. codebase

            Q. Delete xyz.py file
            A. debugger
    '''
    
    response = client.chat.completions.create(
        model = 'gpt-4.1-mini',
        messages = [
            {'role':'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': user_query}
        ]
    )
    
    decision = response.choices[0].message.content.strip().lower()
    
    if 'debugger' in decision:
        return 'debugger'
    return 'codebase'