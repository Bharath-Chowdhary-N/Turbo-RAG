import streamlit as st
import os
from dotenv import load_dotenv
from RAG import RAG

load_dotenv()


st.title("Simple GitHub RAG Chat")


if not os.getenv('OPENAI_API_KEY'):
    st.error("Add OPENAI_API_KEY to your .env file")
    st.stop()


if 'rag' not in st.session_state:
    st.session_state.rag = None
if 'ready' not in st.session_state:
    st.session_state.ready = False


repo_url = st.text_input("GitHub Repository URL:", 
                        placeholder="https://github.com/user/repo")


if st.button("Process Repository"):
    if repo_url:
        with st.spinner("Processing repository..."):
            try:
                st.session_state.rag = RAG(repo_url)
                st.session_state.rag.setup_repo()
                st.session_state.ready = True
                st.success("Repository ready!")
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.error("Enter a repository URL")

if st.session_state.ready and st.session_state.rag:
    st.header("Ask Questions")
    
    question = st.text_input("Your question:", 
                           placeholder="How does the main function work?")
    
    if st.button("Ask") and question:
        with st.spinner("Getting answer..."):
            answer = st.session_state.rag.ask_question(question)
            st.write("**Answer:**")
            st.write(answer)

if st.session_state.ready:
    st.subheader("Quick Questions")
    quick_questions = [
        "What is this project about?",
        "How do I install this?",
        "What are the main functions?",
        "Show me the project structure"
    ]
    
    for q in quick_questions:
        if st.button(q):
            with st.spinner("Getting answer..."):
                answer = st.session_state.rag.ask_question(q)
                st.write(f"**Q:** {q}")
                st.write(f"**A:** {answer}")
                st.markdown("---")