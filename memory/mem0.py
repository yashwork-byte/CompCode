from mem0 import Memory
import os
from dotenv import load_dotenv
load_dotenv()

# Default memory namespace. Pass a real per-user id to isolate memories.
DEFAULT_USER_ID = 'user_A'

# mem0 stores its memories in a separate Qdrant collection from the code index.
MEM_COLLECTION = 'mem0_memories'


# Initialize memory system
def init_memory():
    # NOTE: the key is OPENAI_API_KEY (matches .env and the rest of the app).
    openai_api_key = os.getenv('OPENAI_API_KEY')
    config = {
        'version': 'v1.1',
        'embedder': {
            'provider': 'openai',
            'config': {'api_key': openai_api_key, 'model': 'text-embedding-3-small'}
        },
        'vector_store': {
            'provider': 'qdrant',
            'config': {
                'collection_name': MEM_COLLECTION,
                'host': 'localhost',
                'port': 6333
            }
        }
    }
    return Memory.from_config(config)

# Retrieve relevant past memories
def get_mem_context(mem_client, user_query, user_id=DEFAULT_USER_ID):
    results = mem_client.search(query=user_query, user_id=user_id)
    memories = [mem.get('memory') for mem in results.get('results', [])]
    return '\n'.join(memories[:5])

# Store new interaction
def save_memory(mem_client, user_query, response, user_id=DEFAULT_USER_ID):
    mem_client.add(
        user_id=user_id,
        messages=[
            {'role': 'user', 'content': user_query},
            {'role': 'assistant', 'content': response},
        ]
    )
