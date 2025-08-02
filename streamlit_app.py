import streamlit as st
import os
from sentence_transformers import SentenceTransformer
import anthropic
#from dotenv import load_dotenv
from typing import List, Dict, Any
import time
from datetime import datetime


# Load environment variables for local development only
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # On Streamlit Cloud, this is fine - uses st.secrets instead
    pass

# Handle Pinecone import
try:
    from pinecone import Pinecone
except ImportError:
    st.error("❌ Please update your requirements.txt")
    st.stop()

class PineconeRAGSystem:
    def __init__(self, pinecone_index_name: str = "turbo-rag-index"):
        self.pinecone_index_name = pinecone_index_name
        
        # Initialize Pinecone
        try:
            # Try to get API key from Streamlit secrets first, then environment variables
            pinecone_api_key = st.secrets.get("PINECONE_API_KEY") or os.getenv('PINECONE_API_KEY')
            if not pinecone_api_key:
                st.error("❌ PINECONE_API_KEY not found in secrets or environment variables")
                st.stop()
                
            self.pinecone_client = Pinecone(api_key=pinecone_api_key)
            self.pinecone_index = self.pinecone_client.Index(pinecone_index_name)
        except Exception as e:
            st.error(f"Failed to connect to Pinecone: {e}")
            st.stop()
        
        # Initialize embedding model (same as used in migration)
        @st.cache_resource
        def load_embedder():
            return SentenceTransformer('all-MiniLM-L6-v2')
        
        self.embedder = load_embedder()
        
        # Initialize Anthropic Claude
        try:
            # Try to get API key from Streamlit secrets first, then environment variables
            anthropic_api_key = st.secrets.get("ANTHROPIC_API_KEY") or os.getenv('ANTHROPIC_API_KEY')
            if not anthropic_api_key:
                st.error("❌ ANTHROPIC_API_KEY not found in secrets or environment variables")
                st.stop()
                
            self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
        except Exception as e:
            st.error(f"Failed to initialize Claude: {e}")
            st.stop()
    
    def search_relevant_content(self, query: str, top_k: int = 5, source_filter: str = None) -> List[Dict[str, Any]]:
        """Search for relevant content in Pinecone"""
        try:
            # Create query embedding
            query_embedding = self.embedder.encode([query])[0].tolist()
            
            # Build filter if specified
            filter_dict = None
            if source_filter and source_filter != "both":
                filter_dict = {"source_type": source_filter}
            
            # Search in Pinecone
            results = self.pinecone_index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict
            )
            
            # Format results
            search_results = []
            for match in results['matches']:
                search_results.append({
                    'id': match['id'],
                    'score': match['score'],
                    'content': match['metadata'].get('content_preview', ''),
                    'source_type': match['metadata'].get('source_type', 'unknown'),
                    'file_path': match['metadata'].get('file_path', ''),
                    'channel': match['metadata'].get('channel', ''),
                    'user': match['metadata'].get('user', ''),
                    'timestamp': match['metadata'].get('timestamp', ''),
                    'metadata': match['metadata']
                })
            
            return search_results
            
        except Exception as e:
            st.error(f"Search error: {e}")
            return []
    
    def generate_context(self, search_results: List[Dict[str, Any]]) -> str:
        """Generate context from search results for the LLM"""
        if not search_results:
            return "No relevant content found."
        
        context_parts = []
        
        for i, result in enumerate(search_results, 1):
            source_type = result['source_type']
            content = result['content']
            
            if source_type == 'github':
                file_path = result['file_path']
                context_part = f"[GitHub Code - {file_path}]\n{content}\n"
            elif source_type == 'slack':
                channel = result['channel']
                user = result['user']
                timestamp = result['timestamp']
                context_part = f"[Slack - #{channel} - {user} at {timestamp}]\n{content}\n"
            else:
                context_part = f"[Source: {source_type}]\n{content}\n"
            
            context_parts.append(context_part)
        
        return "\n---\n".join(context_parts)
    
    def ask_question(self, question: str, source_filter: str = "both", top_k: int = 5) -> Dict[str, Any]:
        """Ask a question and get an AI-generated response"""
        start_time = time.time()
        
        # Search for relevant content
        search_results = self.search_relevant_content(question, top_k, source_filter)
        
        if not search_results:
            return {
                'answer': "I couldn't find relevant information for your question. Please try rephrasing or ask about specific topics related to your GitHub repository or Slack conversations.",
                'sources': [],
                'search_time': time.time() - start_time,
                'response_time': 0,
                'context_used': 0
            }
        
        # Generate context
        context = self.generate_context(search_results)
        
        # Create prompt
        prompt = self._create_prompt(question, context, source_filter)
        
        # Get response from Claude
        response_start = time.time()
        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            answer = response.content[0].text
            response_time = time.time() - response_start
            
            return {
                'answer': answer,
                'sources': search_results,
                'search_time': time.time() - start_time,
                'response_time': response_time,
                'context_used': len(search_results)
            }
            
        except Exception as e:
            return {
                'answer': f"Error generating response: {str(e)}",
                'sources': search_results,
                'search_time': time.time() - start_time,
                'response_time': 0,
                'context_used': len(search_results)
            }
    
    def _create_prompt(self, question: str, context: str, source_filter: str) -> str:
        """Create a detailed prompt for Claude"""
        source_description = {
            "github": "GitHub repository code and documentation",
            "slack": "Slack team conversations and discussions", 
            "both": "both GitHub repository and Slack conversations"
        }
        
        prompt = f"""You are an expert assistant with access to {source_description.get(source_filter, 'various sources')}. 

Based on the following relevant information, please provide a comprehensive and helpful answer to the user's question.

RELEVANT INFORMATION:
{context}

USER QUESTION: {question}

INSTRUCTIONS:
1. Provide a clear, detailed answer based on the information above
2. If the question is about code, explain how it works and provide examples where relevant
3. If the question is about team discussions, summarize the key points and decisions
4. If combining information from multiple sources, clearly explain the connections
5. If the information is insufficient, clearly state what's missing
6. Use a helpful, professional tone
7. Format code snippets with proper markdown when discussing code

ANSWER:"""
        
        return prompt
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the Pinecone index"""
        try:
            stats = self.pinecone_index.describe_index_stats()
            return {
                'total_vectors': stats.get('total_vector_count', 0),
                'index_fullness': stats.get('index_fullness', 0),
                'namespaces': stats.get('namespaces', {})
            }
        except Exception as e:
            st.error(f"Error getting index stats: {e}")
            return {}

def main():
    # Page configuration
    st.set_page_config(
        page_title="Turbo RAG Assistant",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 1rem;
        border-radius: 0.5rem;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .source-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.75rem;
        font-weight: bold;
        margin-right: 0.5rem;
    }
    .github-badge {
        background-color: #28a745;
        color: white;
    }
    .slack-badge {
        background-color: #4a154b;
        color: white;
    }
    .stats-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #007bff;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🚀 Turbo RAG Assistant</h1>
        <p>Ask questions about your GitHub repository and Slack conversations</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check API keys from both sources
    pinecone_key = st.secrets.get("PINECONE_API_KEY") or os.getenv('PINECONE_API_KEY')
    anthropic_key = st.secrets.get("ANTHROPIC_API_KEY") or os.getenv('ANTHROPIC_API_KEY')
    
    if not pinecone_key or not anthropic_key:
        st.error("🔑 Please set your API keys:")
        st.markdown("""
        **For local development:** Create a `.env` file with:
        ```
        PINECONE_API_KEY=your_pinecone_key
        ANTHROPIC_API_KEY=your_anthropic_key
        ```
        
        **For Streamlit Cloud:** Add secrets in your app dashboard:
        - Go to your app settings
        - Click "Secrets" 
        - Add your API keys
        """)
        st.stop()
    
    # Initialize RAG system
    @st.cache_resource
    def init_rag_system():
        return PineconeRAGSystem(pinecone_index_name="turbo-rag-index")
    
    try:
        rag_system = init_rag_system()
        st.success("✅ Connected to Pinecone and Claude successfully!")
    except Exception as e:
        st.error(f"❌ Failed to initialize RAG system: {e}")
        st.stop()
    
    # Sidebar
    with st.sidebar:
        st.header("🎛️ Settings")
        
        # Source filter
        source_filter = st.selectbox(
            "Search in:",
            options=["both", "github", "slack"],
            format_func=lambda x: {
                "both": "🔍 Both GitHub & Slack",
                "github": "💻 GitHub Repository Only", 
                "slack": "💬 Slack Messages Only"
            }[x],
            help="Choose which sources to search in"
        )
        
        # Number of results
        top_k = st.slider(
            "Number of results to retrieve:",
            min_value=3,
            max_value=10,
            value=5,
            help="More results provide more context but may slow down responses"
        )
        
        # Index statistics
        st.subheader("📊 Database Stats")
        with st.spinner("Loading stats..."):
            stats = rag_system.get_index_stats()
            
        if stats:
            st.markdown(f"""
            <div class="stats-container">
                <strong>Total Documents:</strong> {stats.get('total_vectors', 0):,}<br>
                <strong>Index Fullness:</strong> {stats.get('index_fullness', 0):.1%}
            </div>
            """, unsafe_allow_html=True)
        
        # Example questions
        st.subheader("💡 Example Questions")
        example_questions = [
            "How does authentication work in the system?",
            "What did the team discuss about the API design?",
            "Show me the main functions in the turbo control code",
            "What issues were mentioned in Slack about deployment?",
            "How is the database configured?",
            "What are the recent decisions about the architecture?"
        ]
        
        for question in example_questions:
            if st.button(question, key=f"example_{hash(question)}", use_container_width=True):
                st.session_state.example_question = question
    
    # Main content area
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("💬 Ask Your Question")
        
        # Handle example question selection
        default_question = ""
        if 'example_question' in st.session_state:
            default_question = st.session_state.example_question
            del st.session_state.example_question
        
        # Question input
        question = st.text_area(
            "Enter your question:",
            value=default_question,
            height=100,
            placeholder="e.g., How does the authentication system work? What did the team decide about the database schema?",
            help="Ask anything about your GitHub repository code or Slack team discussions"
        )
        
        # Submit button
        if st.button("🔍 Search & Answer", type="primary", use_container_width=True):
            if question.strip():
                with st.spinner("🔍 Searching for relevant information..."):
                    # Get answer
                    result = rag_system.ask_question(question, source_filter, top_k)
                    
                    # Display answer
                    st.subheader("💡 Answer")
                    st.markdown(result['answer'])
                    
                    # Display performance metrics
                    st.caption(f"⏱️ Search: {result['search_time']:.2f}s | Response: {result['response_time']:.2f}s | Sources: {result['context_used']}")
                    
                    # Display sources
                    if result['sources']:
                        st.subheader("📚 Sources")
                        
                        for i, source in enumerate(result['sources'], 1):
                            with st.expander(f"Source {i} - {source['source_type'].title()} (Score: {source['score']:.3f})"):
                                if source['source_type'] == 'github':
                                    st.markdown(f"**📁 File:** `{source['file_path']}`")
                                elif source['source_type'] == 'slack':
                                    st.markdown(f"**💬 Channel:** #{source['channel']}")
                                    st.markdown(f"**👤 User:** {source['user']}")
                                    st.markdown(f"**📅 Time:** {source['timestamp']}")
                                
                                st.markdown("**Content:**")
                                st.text(source['content'][:500] + "..." if len(source['content']) > 500 else source['content'])
            else:
                st.warning("Please enter a question to search for answers.")
    
    with col2:
        st.subheader("🎯 Quick Actions")
        
        # Quick search buttons
        quick_searches = [
            ("🔐 Authentication", "How does user authentication work?"),
            ("🗄️ Database", "How is the database structured and configured?"),
            ("🚀 Deployment", "What is the deployment process?"),
            ("🐛 Issues", "What bugs or issues were recently discussed?"),
            ("📋 Meetings", "Summarize recent team meetings and decisions"),
            ("⚙️ Configuration", "Show me the system configuration")
        ]
        
        for label, query in quick_searches:
            if st.button(label, use_container_width=True):
                st.session_state.quick_query = query
                st.rerun()
        
        # Handle quick query
        if 'quick_query' in st.session_state:
            question = st.session_state.quick_query
            del st.session_state.quick_query
            
            with st.spinner("🔍 Searching..."):
                result = rag_system.ask_question(question, source_filter, top_k)
                
                st.subheader("💡 Quick Answer")
                st.markdown(result['answer'])
                
                if result['sources']:
                    st.caption(f"Found {len(result['sources'])} relevant sources")
    
    # Footer
    st.markdown("---")
    st.markdown(
        "💡 **Tip:** Try asking specific questions about your code, team discussions, or system architecture. "
        "The more specific your question, the better the answer!"
    )

if __name__ == "__main__":
    main()