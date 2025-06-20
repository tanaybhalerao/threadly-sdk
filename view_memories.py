from db_setup import SessionLocal
from models import MemoryEvent

def get_all_memories(user_id=None):
    session = SessionLocal()

    if user_id:
        memories = session.query(MemoryEvent).filter(MemoryEvent.user_id == user_id).all()
    else:
        memories = session.query(MemoryEvent).all()

    for mem in memories:
        print("="*40)
        print(f"User ID: {mem.user_id}")
        print(f"Message: {mem.message_text}")
        print(f"Response: {mem.response_text}")
        print(f"Sentiment: {mem.sentiment}")
        print(f"Tags: {mem.tags}")
        print(f"Timestamp: {mem.timestamp}")
        print(f"Importance Score: {mem.importance_score}")

    session.close()

# Run this:
get_all_memories("tanay_001")
