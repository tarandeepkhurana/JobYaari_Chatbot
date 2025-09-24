import streamlit as st
import requests

st.set_page_config(page_title="Job Assistant Chatbot", page_icon="💼")
st.title("💬 Job Assistant Chatbot")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Input box
query = st.chat_input("Ask me about jobs...")

if query:
    # Add user message
    st.session_state["messages"].append({"role": "user", "content": query})

    # Call FastAPI backend
    response = requests.post(
        "http://chatbot:5000/chat",
        json={"query": query, "chat_history": st.session_state["messages"]}
    )
    bot_reply = response.json().get("answer", "⚠️ Something went wrong.")

    # Add bot reply
    st.session_state["messages"].append({"role": "bot", "content": bot_reply})

# Display all messages
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
