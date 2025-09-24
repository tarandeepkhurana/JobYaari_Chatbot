# 💼 JobLens AI Chatbot

JobLens is an AI-powered assistant designed to help users explore and query job opportunities in a conversational way.
It integrates multiple components — backend, frontend, chatbot logic, and a scraper — to provide an end-to-end system.

---

## 🧠 How It Works

1. User enters a job-related query in the **Streamlit frontend**.  
2. Query is sent to the **FastAPI backend** (`/chat` endpoint).  
3. **Chatbot pipeline**:  
   - Converts query into embeddings using `SentenceTransformer`.  
   - Searches **ChromaDB** for relevant job postings.  
   - Builds a prompt with retrieved jobs + conversation history.  
   - Passes the prompt to **Gemini 2.5 Pro** via **LangChain**.  
   - Response is returned back to the frontend and displayed in chat.  
4. Meanwhile, a **scraper service** runs every **20 minutes** to fetch the latest job postings from [Jobyaari](https://www.jobyaari.com/) and updates **ChromaDB**, ensuring the chatbot always has fresh job data.  

---

## ⚙️ Components

### 1. **Chatbot (src/chatbot)**
- Uses **LangChain** + **Google Gemini API** for natural language responses.
- Fetches jobs information from **ChromaDB** based on user query.
- Uses **Sentence Transformers** (`all-MiniLM-L6-v2`) for vector embeddings.
- Maintains conversational context with `ConversationBufferMemory`.

### 2. **Backend (src/backend)**
- Built with **FastAPI**.
- Provides REST API endpoints (e.g., `/chat`) for chatbot queries.
- Connects frontend ↔ chatbot logic.

### 3. **Frontend (src/frontend)**
- Built with **Streamlit**.
- Provides a simple chat-style UI for users to ask questions.
- Calls FastAPI backend using HTTP requests.

### 4. **Scraper (src/scraper)**
- Responsible for collecting job postings from external sources.
- Populates ChromaDB with job embeddings (title, organization, location, salary, deadlines, etc.).

---

## 🛠️ Tech Stack

| Component   | Technology / Tool                        |
|-------------|-------------------------------------------|
| Frontend    | Streamlit                                |
| Backend     | FastAPI                                  |
| LLM         | Google Gemini (via LangChain)            |
| Embeddings  | SentenceTransformers (`all-MiniLM-L6-v2`)|
| Vector Store| ChromaDB                                 |
| Scraper     | Python (`Selenium`, `BeautifulSoup`, `requests`, etc.)|

---

## ✨ Future Improvements

- Containerization with Docker (in progress).
- Multi-user chat sessions.
- Advanced job filtering (salary, role, location).
- Deployment to cloud (AWS/GCP/Azure).

---
## 📌 Data Source

This project scrapes job postings directly from the [Jobyaari](https://www.jobyaari.com/) website.  
The scraped job data is stored in **ChromaDB** and used by the chatbot to provide relevant responses to user queries.


