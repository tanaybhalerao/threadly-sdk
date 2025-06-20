from embedding_utils import init_faiss, search_memory, add_to_memory

# Step 1: Init FAISS index
init_faiss()

# Step 2: (Optional) Add some fake memories if needed for quick testing
add_to_memory("I asked for a refund three times", {"user_id": "tanay_001"})
add_to_memory("Why is my payment taking so long?", {"user_id": "tanay_001"})
add_to_memory("This delay is making me angry", {"user_id": "tanay_001"})
add_to_memory("Thank you, I finally got my refund", {"user_id": "tanay_001"})
add_to_memory("Can I speak to someone about billing?", {"user_id": "tanay_001"})

# Step 3: Search memory
query = "What am I feeling?"
results = search_memory(query, top_k=3)

# Step 4: Print matches
print(f"\n🔍 Query: {query}")
print("🔁 Top Semantic Matches:\n")
for i, (text, metadata, _) in enumerate(results):
    print(f"{i+1}. {text}")
    print(f"   ↳ Metadata: {metadata}")
    print("-" * 40)
