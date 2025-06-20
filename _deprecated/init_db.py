from db_setup import engine
from models import Base

# Create all tables defined with Base (just MemoryEvent for now)
Base.metadata.create_all(bind=engine)

print("Database and tables created.")
