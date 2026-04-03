from dotenv import load_dotenv
load_dotenv()

from ingestion.code_ingest import extract_chunks
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI
client = OpenAI()

def generate_summary(chunk):
    prompt = f'''
    You are summarizing a function for comprehension purposes.
        
        Focus on 
        - what the function does
        - key logic
        - important dependencies
    
    Function Name : {chunk['function']}
    Code : {chunk['code']}
    '''

    response = client.chat.completions.create(
        model = 'gpt-4.1-mini',
        messages = [
            {'role': 'user', 'content': prompt}
        ]
    )
    
    return response.choices[0].message.content

def process_chunk(chunk):
    summary = generate_summary(chunk)

    text = f"""
    Function: {chunk['function']}
    Summary: {summary}
    """

    metadata = {
        "function": chunk["function"],
        "file": chunk["file"],
        "code": chunk["code"],
        "summary": summary
    }

    return text, metadata

def index_repo(repo_path):
    chunks = extract_chunks(repo_path)

    texts = []
    metadatas = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(process_chunk, chunks))

    for text, metadata in results:
        texts.append(text)
        metadatas.append(metadata)
    
    embedding_model = OpenAIEmbeddings(
        model = 'text-embedding-3-small'
    )
    
    vector_store = QdrantVectorStore.from_texts(
        texts = texts,
        metadatas = metadatas,
        embedding = embedding_model,
        url = 'http://localhost:6333',
        collection_name = 'codebase'
    )
    
    print('Indexing completed')