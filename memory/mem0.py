from mem0 import Memory
import os
from dotenv import load_dotenv
load_dotenv()

def init_memory():
    OPEN_API_KEY = os.getenv('OPEN_API_KEY')
    config = {
    'version': 'v1.1',
    'embedder':{
        'provider': 'openai',
        'config': {'api_key': OPEN_API_KEY, 'model': 'text-embedding-3-small'}
        },
    'vector_store':{
        'provider': 'qdrant',
        'config': {
            'host': 'localhost',
            'port': '6333'
            }
        }
    }
    return Memory.from_config(config)

def get_mem_context(mem_client, user_query):
    results = mem_client.search(query = user_query, user_id = 'user_yash')
    memories = [mem.get('memory') for mem in results.get('results', [])]
    return '\n'.join(memories[:5])

def save_memory(mem_client, user_query, response):
    mem_client.add(
        user_id = 'user_yash',
        messages = [
            {'role':'user','content': user_query},
            {'role':'assistant','content': response},
        ]
    )