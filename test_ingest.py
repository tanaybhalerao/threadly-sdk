from memory_ingestion import ingest_message
from embedding_utils import init_faiss
init_faiss()

# Simulate a user sending a message
user_id = "tanay_001"
message_text = "I’ve contacted support three times and still haven’t received my refund. This is so frustrating!"
response_text = "I'm really sorry about the delay, Tanay. Let me look into this for you."

# Just call the ingestion function — do not redefine it
ingest_message(
    user_id=user_id,
    message_text=message_text,
    response_text=response_text,
    topic="refund"
)
