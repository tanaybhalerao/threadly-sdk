from embedding_utils import init_faiss, add_to_memory, search_memory

# Step 1: Initialize FAISS vector index
init_faiss()

# Step 2: Add messages (simulate user history)
add_to_memory("I need help with my order", {"user_id": "tanay_001"})
add_to_memory("Where is my refund?", {"user_id": "tanay_001"})
add_to_memory("The product never arrived", {"user_id": "tanay_001"})
add_to_memory("Can I speak to someone about a billing issue?", {"user_id": "tanay_001"})
add_to_memory("I love how fast your service is!", {"user_id": "tanay_001"})
add_to_memory("Do you offer next-day shipping?", {"user_id": "tanay_001"})

# Step 3: Try a search query
query = "I am a bit frustrated with my order"
results = search_memory(query)

print(f"\n🔍 Query: {query}")
print("🔁 Top Matches:")
for i, (text, metadata, _) in enumerate(results):
    print(f"{i+1}. {text}")
