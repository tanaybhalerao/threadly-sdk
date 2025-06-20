import os
import faiss
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)
EMBEDDING_MODEL = "text-embedding-3-small"

# Vector index and memory store
memory_index = None
memory_data = []

# Thread-level signature store
thread_signature_index = None
thread_signature_data = []

def normalize_vector(vec):
    vec = np.array(vec, dtype='float32')
    return vec / np.linalg.norm(vec)

def get_embedding(text):
    text = (text or "").strip()
    if not text:
        raise ValueError("❌ Cannot embed empty input.")

    response = client.embeddings.create(
        input=[text],
        model=EMBEDDING_MODEL
    )
    return response.data[0].embedding

def init_faiss(dim=1536):
    global memory_index, memory_data, thread_signature_index, thread_signature_data
    memory_index = faiss.IndexFlatL2(dim)
    memory_data = []
    thread_signature_index = faiss.IndexFlatL2(dim)
    thread_signature_data = []
    print(f"[{timestamp()}] 🧹 FAISS indexes re-initialized.")

def add_to_memory(text, metadata):
    embedding = get_embedding(text)
    vector = np.array([normalize_vector(embedding)], dtype='float32')
    memory_index.add(vector)
    memory_data.append((text, metadata, vector))
    print(f"[{timestamp()}] 🧠 Added to vector memory: {text[:50]}... | user_id={metadata.get('user_id')}")
    print(f"[{timestamp()}] 🧠 Current vector memory count: {len(memory_data)}")

def search_memory(query_text, top_k=5, user_id=None, thread_id=None):
    query_vector = get_embedding(query_text)
    query_vector = normalize_vector(query_vector).reshape(1, -1)

    D, I = memory_index.search(query_vector, top_k * 3)
    results = []
    seen_texts = set()

    for i in I[0]:
        if i < 0 or i >= len(memory_data):
            continue
        text, metadata, vector = memory_data[i]
        if (user_id is None or metadata.get("user_id") == user_id) and \
           (thread_id is None or metadata.get("thread_id") == thread_id):
            if text not in seen_texts:
                results.append((text, metadata, vector))
                seen_texts.add(text)

        if len(results) >= top_k:
            break

    print(f"[{timestamp()}] 🔍 Vector search returned {len(results)} hits for user={user_id} thread={thread_id}")
    return results

# ------------------------------
# THREAD SIGNATURE FUNCTIONS
# ------------------------------

def add_thread_signature(thread_id, user_id, text):
    embedding = get_embedding(text)
    vector = np.array([normalize_vector(embedding)], dtype='float32')
    thread_signature_index.add(vector)
    thread_signature_data.append((thread_id, user_id, vector))
    print(f"[{timestamp()}] 🧷 Thread signature added for {thread_id} (user: {user_id})")

def search_thread_signatures(text, user_id, top_k=5):
    query_vector = normalize_vector(get_embedding(text)).reshape(1, -1)
    D, I = thread_signature_index.search(query_vector, top_k)
    results = []

    for i in I[0]:
        if i < 0 or i >= len(thread_signature_data):
            continue
        tid, uid, vector = thread_signature_data[i]
        if uid == user_id:
            results.append((tid, vector))

    print(f"[{timestamp()}] 🔁 Thread signature match returned {len(results)} threads")
    return results

def print_vector_count():
    print(f"[{timestamp()}] 🧠 Message memory: {len(memory_data)} | Thread signatures: {len(thread_signature_data)}")

def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
