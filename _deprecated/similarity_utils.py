import difflib
import logging
from typing import List, Tuple
import numpy as np
from embedding_utils import get_embedding, normalize_vector

logging.basicConfig(level=logging.INFO)

SIMILARITY_THRESHOLD = 0.6
SHORT_NUANCE_THRESHOLD = 5  # words
BOOST_FOR_SHORT_MATCH = 0.15  # additional score if match is good but short

def get_nuance_similarity(current: str, previous: str) -> float:
    """
    Compute a fuzzy similarity score between two nuances using difflib,
    with a boost for short but semantically relevant messages.
    """
    if not current or not previous:
        return 0.0

    raw_score = difflib.SequenceMatcher(None, current.lower(), previous.lower()).ratio()

    # Boost for short emotionally intense phrases (e.g., "Where is my money")
    word_count = min(len(current.split()), len(previous.split()))
    boost = BOOST_FOR_SHORT_MATCH if (raw_score > 0.5 and word_count <= SHORT_NUANCE_THRESHOLD) else 0.0
    score = min(raw_score + boost, 1.0)

    logging.info(f"🔍 Nuance similarity between '{current}' and '{previous}': {score:.2f}")
    return score


def is_similar_nuance(current: str, previous: str, threshold: float = SIMILARITY_THRESHOLD) -> bool:
    return get_nuance_similarity(current, previous) >= threshold


def batch_nuance_similarity(current: str, references: List[str], threshold: float = SIMILARITY_THRESHOLD) -> List[Tuple[str, float]]:
    """
    Given a current nuance and a list of previous ones, return those that exceed the similarity threshold.
    """
    results = []
    for ref in references:
        score = get_nuance_similarity(current, ref)
        if score >= threshold:
            results.append((ref, score))
    return sorted(results, key=lambda x: x[1], reverse=True)


def get_embedding_similarity(text_a: str, text_b: str) -> float:
    """
    Compute cosine similarity between the embeddings of two texts.
    """
    try:
        vec_a = normalize_vector(get_embedding(text_a))
        vec_b = normalize_vector(get_embedding(text_b))
        similarity = float(np.dot(vec_a, vec_b))
        logging.info(f"🧠 Embedding similarity between A and B: {similarity:.3f}")
        return similarity
    except Exception as e:
        logging.warning(f"⚠️ Embedding similarity error: {e}")
        return 0.0
