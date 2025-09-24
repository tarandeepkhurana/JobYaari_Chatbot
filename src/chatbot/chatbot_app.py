from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import chromadb
import logging

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Silence noisy libraries
logging.getLogger("chromadb").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

logger = logging.getLogger("chatbot_app.py")

load_dotenv()

# Initialize Chroma client
client = chromadb.HttpClient(host="chroma", port=8000)

# Create / get collection
collection = client.get_or_create_collection(
    name="jobs_collection",
    metadata={"hnsw:space": "cosine"}
)

# Embedding model
embedder = SentenceTransformer("src/chatbot/all-MiniLM-L6-v2")

# Memory (chat history is retained)
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

def final_response_by_llm(user_query: str) -> str:
    """
    Takes a user query, retrieves relevant jobs from Chroma,
    and generates a conversational answer using Groq LLM with memory.
    """

    # Step 1: Encode user query
    query_embedding = embedder.encode(user_query).tolist()

    # Step 2: Search in Chroma
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5,
        include=["metadatas"]
    )

    # If no jobs found
    if not results.get("metadatas"):
        return "I couldn’t find any matching jobs right now. Please try again later."

    # Extract top jobs
    filtered_jobs = results["metadatas"][0]

    # Step 3: Build prompt with memory + jobs
    answer_template = """
    You are a helpful job assistant chatbot. 
    The user asked: "{query}".

    Conversation so far:
    {chat_history}

    Here are the most relevant jobs from the database (may not be exhaustive):
    {filtered_jobs}

    Now:
    1. Answer the user's query clearly and naturally.
    2. If multiple jobs match, summarize them in a neat list with key details:
    - title, organization, location, last_date, salary.
    3. If relevant jobs are missing or not enough, acknowledge it and suggest searching again with different keywords.
    4. Always keep the response conversational but accurate. Be concise and useful.
    """

    # Initialize Gemini 2.5 Pro
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        temperature=0,          
        max_output_tokens=65535    
    )

    parser = StrOutputParser()

    prompt = PromptTemplate(
        template=answer_template,
        input_variables=["query", "filtered_jobs", "chat_history"]
    )

    chain = prompt | llm | parser

    response = chain.invoke({
        "query": user_query,
        "filtered_jobs": filtered_jobs,
        "chat_history": memory.load_memory_variables({}).get("chat_history", [])
    })
    
    # Save conversation turn
    memory.save_context({"query": user_query}, {"response": response})

    return response

if __name__ == "__main__":
    print("🤖 Chatbot is ready! Type your queries below (type 'exit' to quit)\n")
    while True:
        query = input("You: ")
        if query.lower() in ["exit", "quit", "q"]:
            print("👋 Goodbye!")
            break
        try:
            response = final_response_by_llm(query)
            print(f"Bot: {response}\n")
        except Exception as e:
            print(f"⚠️ Error: {e}\n")
