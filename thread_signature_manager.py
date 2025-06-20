import faiss
import numpy as np
from typing import List, Dict, Tuple
from embedding_utils import get_embedding, normalize_vector

# Global FAISS index and store
THREAD_SIGNATURE_DIM = 1536
thread_signature_index = faiss.IndexFlatL2(THREAD_SIGNATURE_DIM)
thread_signature_store: Dict[str, Dict] = {}  # thread_id -> {"vector": ..., "metadata": {...}}

def add_thread_signature(thread_id: str, user_id: str, message_text: str):
    """
    Add a thread signature using the first message of the thread.
    This is a lightweight version using a single message vector.
    """
    if not message_text:
        return

    embedding = normalize_vector(get_embedding(message_text))
    thread_signature_index.add(np.array([embedding], dtype='float32'))
    thread_signature_store[thread_id] = {
        "vector": embedding,
        "metadata": {"user_id": user_id}
    }
    print(f"✅ Thread signature stored for {thread_id} | user_id={user_id}")

def search_thread_signatures(query_text: str, user_id: str, top_k=5) -> List[Tuple[str, float]]:
    """
    Search for top_k most similar thread signatures by vector similarity.
    Returns list of (thread_id, similarity_score).
    """
    if not thread_signature_store:
        return []

    query_vector = normalize_vector(get_embedding(query_text)).reshape(1, -1)
    D, I = thread_signature_index.search(query_vector, top_k)

    results = []
    all_thread_ids = list(thread_signature_store.keys())
    for i, distance in zip(I[0], D[0]):
        if i < len(all_thread_ids):
            thread_id = all_thread_ids[i]
            metadata = thread_signature_store[thread_id]["metadata"]
            if metadata.get("user_id") == user_id:
                similarity_score = 1.0 - distance  # FAISS returns L2 distance, convert to similarity
                results.append((thread_id, similarity_score))

    print(f"🔁 Found {len(results)} similar thread(s) for user_id={user_id}")
    return results

def print_thread_signature_stats():
    print(f"🧠 Total stored thread signatures: {len(thread_signature_store)}")
