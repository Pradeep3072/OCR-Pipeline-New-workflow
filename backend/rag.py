import os
import hashlib
from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer
from groq import Groq
from logger import get_logger

logger = get_logger(__name__)

MILVUS_DB_PATH = os.path.join(os.path.dirname(__file__), "db", "milvus_demo.db")
COLLECTION_NAME = "ocr_documents"
EMBEDDING_DIM = 384 # Dimension for all-MiniLM-L6-v2

embedding_model = None
milvus_client = None
groq_client = None

def init_services():
    global embedding_model, milvus_client, groq_client
    
    if embedding_model is None:
        logger.info("Loading sentence-transformer model for RAG...")
        # Note: on first run, this downloads the model (~80MB)
        embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    
    if milvus_client is None:
        logger.info(f"Connecting to Milvus Lite at {MILVUS_DB_PATH}")
        milvus_client = MilvusClient(MILVUS_DB_PATH)
        
        # Check and create collection
        if not milvus_client.has_collection(collection_name=COLLECTION_NAME):
            milvus_client.create_collection(
                collection_name=COLLECTION_NAME,
                dimension=EMBEDDING_DIM
            )
            logger.info(f"Created Milvus collection: {COLLECTION_NAME}")
            
    if groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if api_key and api_key != "your_groq_api_key_here":
            groq_client = Groq(api_key=api_key)
        else:
            logger.warning("GROQ_API_KEY is not set or invalid. RAG generation will fail.")

def chunk_text(text, chunk_size=300, overlap=50):
    """Splits text into overlapping chunks of words."""
    words = text.split()
    chunks = []
    if not words:
        return chunks
        
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

def index_document(task_id: str, text: str):
    """Embeds the OCR text chunks and stores them in Milvus."""
    init_services()
    if not text.strip():
        logger.warning(f"No text to index for {task_id}")
        return
        
    chunks = chunk_text(text)
    if not chunks:
        return
        
    logger.info(f"Embedding {len(chunks)} chunks for {task_id}...")
    embeddings = embedding_model.encode(chunks)
    
    data = []
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        # Generate a deterministic positive integer ID
        chunk_id_str = f"{task_id}_{i}"
        chunk_id = int(hashlib.sha256(chunk_id_str.encode()).hexdigest()[:15], 16)
        
        data.append({
            "id": chunk_id,
            "task_id": task_id,
            "vector": emb.tolist(),
            "text": chunk
        })
        
    milvus_client.insert(collection_name=COLLECTION_NAME, data=data)
    logger.info(f"Successfully indexed {len(data)} vectors for {task_id}")

def ask_question(task_id: str, question: str) -> str:
    """Retrieves relevant chunks and generates an answer using Groq API."""
    init_services()
    if not groq_client:
        return {"answer": "Error: GROQ_API_KEY is not configured on the server. Please add it to your .env file.", "contexts": []}
        
    logger.info(f"Answering question for {task_id}: {question}")
    
    # 1. Embed the question
    q_emb = embedding_model.encode([question])[0]
    
    # 2. Search Milvus for top 3 matching chunks
    search_res = milvus_client.search(
        collection_name=COLLECTION_NAME,
        data=[q_emb.tolist()],
        filter=f'task_id == "{task_id}"',
        limit=3,
        output_fields=["text"]
    )
    
    contexts = []
    if search_res and len(search_res[0]) > 0:
        for hit in search_res[0]:
            contexts.append(hit['entity']['text'])
            
    if not contexts:
        try:
            from db.session import SessionLocal
            from db.models import Document
            db = SessionLocal()
            doc = db.query(Document).filter(Document.task_id == task_id).first()
            if doc and doc.status == "SUCCESS" and doc.result_data:
                logger.info(f"Document {task_id} not in Milvus. Lazy Indexing now...")
                full_text = " ".join([res["result_data"]["text"] for res in doc.result_data])
                index_document(task_id, full_text)
                
                # Retry search
                search_res = milvus_client.search(
                    collection_name=COLLECTION_NAME,
                    data=[q_emb.tolist()],
                    filter=f'task_id == "{task_id}"',
                    limit=3,
                    output_fields=["text"]
                )
                if search_res and len(search_res[0]) > 0:
                    for hit in search_res[0]:
                        contexts.append(hit['entity']['text'])
            db.close()
        except Exception as e:
            logger.error(f"Error during lazy indexing: {e}")
            
    if not contexts:
        return {"answer": "I could not find any relevant text in the scanned document to answer your question.", "contexts": []}
        
    context_str = "\n\n---\n\n".join(contexts)
    
    # 3. Prompt Groq LLM
    prompt = f"""You are a helpful and intelligent AI assistant. 
Your task is to answer the user's question based strictly on the provided OCR document context. 
If the answer cannot be found in the context, explicitly say that you do not know.

DOCUMENT CONTEXT:
{context_str}

USER QUESTION: {question}

ANSWER:"""
    
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="openai/gpt-oss-20b", # Selected from available models
            temperature=0.2,
            max_tokens=1024,
        )
        return {"answer": chat_completion.choices[0].message.content, "contexts": contexts}
    except Exception as e:
        logger.error(f"Groq API Error: {e}")
        return {"answer": f"Error communicating with the LLM API: {str(e)}", "contexts": contexts}

def evaluate_answer(question: str, answer: str, contexts: list) -> dict:
    """Evaluates the RAG response using Ragas framework."""
    if not contexts or "Error" in answer or "I could not find any relevant text" in answer:
        return {"faithfulness": 0.0, "answer_relevancy": 0.0}
    
def evaluate_answer(question: str, answer: str, contexts: list[str]) -> dict:
    """
    Evaluates the answer for faithfulness and relevancy using a fast, single-pass LLM prompt.
    """
    import os
    import re
    from langchain_groq import ChatGroq
    from langchain_core.prompts import PromptTemplate

    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return {"faithfulness": 0.0, "answer_relevancy": 0.0, "error": "No API key"}
            
        llm = ChatGroq(temperature=0, groq_api_key=api_key, model_name="qwen/qwen3.6-27b", max_retries=1)
        
        context_str = "\n".join(contexts)
        
        prompt = PromptTemplate.from_template("""
        You are an expert evaluator. Evaluate the given answer based on the following two metrics:
        
        1. Faithfulness: Does the answer strictly use information from the Context? (Score 0.0 to 1.0)
        2. Answer Relevancy: How directly does the answer address the Question? (Score 0.0 to 1.0)
        
        Context:
        {context}
        
        Question:
        {question}
        
        Answer:
        {answer}
        
        Return your evaluation exactly in this format:
        Faithfulness: <score>
        Relevancy: <score>
        """)
        
        chain = prompt | llm
        
        logger.info(f"Running Custom LLM Evaluation for question: {question}")
        result = chain.invoke({"context": context_str, "question": question, "answer": answer})
        content = result.content
        
        faithfulness = 0.0
        relevancy = 0.0
        
        faith_match = re.search(r'Faithfulness:\s*([0-9.]+)', content, re.IGNORECASE)
        if faith_match:
            faithfulness = float(faith_match.group(1))
            
        rel_match = re.search(r'Relevancy:\s*([0-9.]+)', content, re.IGNORECASE)
        if rel_match:
            relevancy = float(rel_match.group(1))
            
        return {
            "faithfulness": faithfulness,
            "answer_relevancy": relevancy
        }
    except Exception as e:
        logger.error(f"Custom Evaluation Error: {e}")
        return {"faithfulness": 0.0, "answer_relevancy": 0.0, "error": str(e)}
