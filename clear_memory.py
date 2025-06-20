from db_setup import SessionLocal
from models import MemoryEvent

session = SessionLocal()

# Delete all rows
session.query(MemoryEvent).delete()
session.commit()
session.close()

print("✅ Memory table cleared.")
