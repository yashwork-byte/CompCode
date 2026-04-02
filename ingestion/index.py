from dotenv import load_dotenv
load_dotenv()

from ingestion.code_ingest import extract_chunks
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore

from openai import OpenAI
client = OpenAI()

# def generate_description(chunk):
#     prompt = f'''
#     Explain what this function does in 2-3 lines.
    
#     Function Name : {chunk['function']}
#     Code : {chunk['code']}
#     '''

#     response = client.chat.completions.create(
#         model = 'gpt-4.1-mini',
#         messages = [
#             {'role': 'user', 'content': prompt}
#         ]
#     )
    
#     return response.choices[0].message.content

def index_repo(repo_path):
    chunks = extract_chunks(repo_path)
    
    texts = []
    
    for chunk in chunks:
        # description = generate_description(chunk)
        text = f"""
            Function: {chunk['function']}
            File: {chunk['file']}

            Code: {chunk['code']}
             """
        texts.append(text)
        
    metadatas = chunks
    
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