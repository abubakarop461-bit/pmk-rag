import os
import streamlit as st
import pypdf
from dotenv import load_dotenv
from loguru import logger
from qdrant_client.models import VectorParams, Distance

# Load environment variables from .env if present
load_dotenv()

# Import backend modules
from llm_provider import OpenRouterLLMProvider, SUGGESTED_MODELS
from rag_backend import (
    get_embeddings,
    get_qdrant_client,
    get_vector_store,
    ingest_pdf,
    retrieve_context
)

# Page configuration
st.set_page_config(
    page_title="RAG Prototype - Document Q&A",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium styling
st.markdown("""
<style>
    .reportview-container {
        background: #f0f2f6;
    }
    .main-header {
        font-family: 'Outfit', 'Inter', sans-serif;
        color: #1E3A8A;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-family: 'Inter', sans-serif;
        color: #4B5563;
        margin-bottom: 2rem;
    }
    .status-card {
        background-color: #FFFFFF;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1px solid #E5E7EB;
        margin-bottom: 1rem;
    }
    .success-text {
        color: #10B981;
        font-weight: 600;
    }
    .warning-text {
        color: #F59E0B;
        font-weight: 600;
    }
    .error-text {
        color: #EF4444;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SESSION STATE -----------------
if "processed_files" not in st.session_state:
    st.session_state.processed_files = {}
if "temp_files_to_clean" not in st.session_state:
    st.session_state.temp_files_to_clean = []
if "submitted_question" not in st.session_state:
    st.session_state.submitted_question = ""
if "processing" not in st.session_state:
    st.session_state.processing = False
if "answer" not in st.session_state:
    st.session_state.answer = ""
if "retrieved_docs" not in st.session_state:
    st.session_state.retrieved_docs = []
if "confirmation_message" not in st.session_state:
    st.session_state.confirmation_message = ""

# ----------------- SIDEBAR: SETTINGS & CONFIG -----------------
st.sidebar.markdown("<h2 class='main-header'>⚙️ Configuration</h2>", unsafe_allow_html=True)

# 1. API Key Resolution
env_key = os.getenv("OPENROUTER_API_KEY")
api_key_source = ""
default_key = ""

if env_key:
    api_key_source = " (Loaded from system environment)"
    default_key = env_key
else:
    # Check if a .env file value is active
    if os.path.exists(".env"):
        api_key_source = " (Loaded from local .env)"

st.sidebar.markdown(f"**OpenRouter API Key** {api_key_source}")
api_key_input = st.sidebar.text_input(
    "Enter API Key",
    value=default_key,
    type="password",
    placeholder="sk-or-...",
    help="Enter your OpenRouter API key. If already set as an environment variable or in a .env file, you can leave this blank."
)

api_key = api_key_input if api_key_input else env_key

# 2. Model Selection
st.sidebar.markdown("**Model Settings**")
model_choice = st.sidebar.selectbox(
    "Select LLM Model",
    options=SUGGESTED_MODELS + ["Custom Model..."]
)

if model_choice == "Custom Model...":
    model_name = st.sidebar.text_input("Enter custom model identifier", value="qwen/qwen3-8b")
else:
    model_name = model_choice

# 3. Test LLM Connection Button
if st.sidebar.button("🔌 Test OpenRouter Connection"):
    if not api_key:
        st.sidebar.error("❌ API Key is missing. Please configure it.")
    else:
        with st.sidebar.spinner("Testing API connection..."):
            try:
                tester = OpenRouterLLMProvider(api_key=api_key, model_name=model_name)
                success = tester.test_connection()
                if success:
                    st.sidebar.success("✅ Connection Successful!")
                    logger.info("OpenRouter connection tested successfully via UI.")
                else:
                    st.sidebar.warning("⚠️ Connected, but response was unexpected.")
            except Exception as e:
                st.sidebar.error(f"❌ Connection Failed: {str(e)}")
                logger.error(f"UI connection test failed: {e}")

st.sidebar.divider()

# 4. Mode Configuration
st.sidebar.markdown("<h3 class='main-header'>🌐 Mode Configuration</h3>", unsafe_allow_html=True)
app_mode = st.sidebar.selectbox(
    "Application Mode",
    options=["Single Document Mode", "Multi Document Mode"],
    help="Single Document Mode replaces the previous document. Multi Document Mode allows concurrent indexing of multiple files."
)

# 5. Vector Database Status
st.sidebar.markdown("<h3 class='main-header'>🗄️ Vector Database</h3>", unsafe_allow_html=True)

# Application-wide global caching for Qdrant client connection (guarantees exactly ONE client instance during runtime)
@st.cache_resource
def get_global_qdrant_client():
    client, mode = get_qdrant_client()
    return client, mode

# Application-wide global caching for embeddings (ensures fast startup and single load)
@st.cache_resource
def get_global_embeddings():
    return get_embeddings()

# Retrieve single global client and embeddings instances
db_client, db_mode = get_global_qdrant_client()
embeddings = get_global_embeddings()

if db_mode == "Docker Server":
    st.sidebar.markdown(f"Status: <span class='success-text'>🟢 Running ({db_mode})</span>", unsafe_allow_html=True)
else:
    st.sidebar.markdown(f"Status: <span class='warning-text'>🟡 Disk Persistence ({db_mode})</span>", unsafe_allow_html=True)
    st.sidebar.caption("Qdrant Docker container not found on localhost:6333. Data will be saved locally inside the workspace.")

# Recreate VectorStore wrapper dynamically on every rerun (not cached!)
collection_name = "rag_documents"
try:
    vector_store = get_vector_store(db_client, embeddings, collection_name=collection_name)
    
    # Get active points count
    try:
        status_info = db_client.get_collection(collection_name)
        points_count = status_info.points_count
    except Exception:
        points_count = 0
        
    st.sidebar.metric(label="Total Chunks Indexed", value=points_count)
except Exception as e:
    st.sidebar.error(f"Database Initialization Error: {e}")
    vector_store = None

# 6. Sidebar Debug Panel (Requirement 9)
st.sidebar.divider()
st.sidebar.markdown("<h3 class='main-header'>🛠️ Debug Panel</h3>", unsafe_allow_html=True)
st.sidebar.markdown(f"**Current Collection**: `{collection_name}`")

try:
    total_vectors = db_client.get_collection(collection_name).points_count
except Exception:
    total_vectors = 0
st.sidebar.markdown(f"**Total Vectors**: `{total_vectors}`")

indexed_docs_list = list(st.session_state.processed_files.keys())
indexed_docs_str = ", ".join(indexed_docs_list) if indexed_docs_list else "None"
st.sidebar.markdown(f"**Indexed Document(s)**: `{indexed_docs_str}`")

if st.session_state.retrieved_docs:
    retrieved_names = list(set([doc.metadata.get("filename", "Unknown") for doc in st.session_state.retrieved_docs]))
    retrieved_str = ", ".join(retrieved_names)
else:
    retrieved_str = "None"
st.sidebar.markdown(f"**Retrieved Documents**: `{retrieved_str}`")

# ----------------- MAIN PANEL -----------------
st.markdown("<h1 class='main-header'>🤖 Enterprise RAG Document Q&A</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'>Upload contracts, drawings, specs, reports, or BOQs to instantly search and extract answers with full citations.</p>", unsafe_allow_html=True)

# 1. Document Upload section
st.markdown("### 📤 Upload PDF Documents")

# Set multi-upload option based on the selected mode
is_multi = (app_mode == "Multi Document Mode")
uploaded_input = st.file_uploader(
    "Select PDF file(s) to automatically parse and index" if is_multi else "Select a PDF file to automatically parse and index",
    type=["pdf"],
    accept_multiple_files=is_multi
)

# Convert upload to a unified list structure
if is_multi:
    uploaded_files_list = uploaded_input if uploaded_input is not None else []
else:
    uploaded_files_list = [uploaded_input] if uploaded_input is not None else []

# Clean up session state metadata for files that have been removed by the user
if uploaded_files_list:
    current_names = {f.name for f in uploaded_files_list}
    st.session_state.processed_files = {
        k: v for k, v in st.session_state.processed_files.items() if k in current_names
    }
else:
    st.session_state.processed_files = {}

# Check for new files that need automatic processing
new_files_to_process = []
for f in uploaded_files_list:
    if f.name not in st.session_state.processed_files:
        new_files_to_process.append(f)

# Helper function to clear collection manually and verify counts
def clear_collection_manually_and_verify(client, collection_name):
    # Count before deletion
    try:
        before_count = client.get_collection(collection_name).points_count
    except Exception:
        before_count = 0
    
    logger.info(f"DB RESET: Collection '{collection_name}' has {before_count} vectors before deletion.")
    
    # 1. Delete the collection
    try:
        try:
            exists = client.collection_exists(collection_name)
        except AttributeError:
            collections = client.get_collections().collections
            exists = any(c.name == collection_name for c in collections)
            
        if exists:
            client.delete_collection(collection_name)
    except Exception as e:
        logger.error(f"Error during collection delete: {e}")
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass
            
    # Verify that the collection no longer exists
    import time
    time.sleep(0.3)
    try:
        exists_after = client.collection_exists(collection_name)
    except AttributeError:
        collections = client.get_collections().collections
        exists_after = any(c.name == collection_name for c in collections)
        
    if exists_after:
        logger.error(f"VERIFICATION FAILURE: Collection '{collection_name}' still exists after deletion!")
        raise RuntimeError("Collection deletion failed verification.")
    else:
        logger.info("VERIFICATION SUCCESS: Collection deleted successfully.")
        
    # Recreate the collection
    from qdrant_client.models import Distance, VectorParams
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )
    time.sleep(0.3)
    
    # 2. Verify collection contains exactly 0 vectors
    try:
        after_count = client.get_collection(collection_name).points_count
    except Exception:
        after_count = 0
        
    logger.info(f"DB RESET: Collection '{collection_name}' has {after_count} vectors after recreation.")
    if after_count != 0:
        logger.error(f"VERIFICATION FAILURE: Collection recreation failed, contains {after_count} vectors instead of 0!")
        raise RuntimeError("Collection recreation count verification failed.")
        
    return before_count, after_count

# Automatically process newly uploaded files
if new_files_to_process:
    if vector_store is None:
        st.error("Cannot index: Vector Database is not initialized correctly.")
    else:
        # If Single Document Mode, perform complete session and DB reset
        before_count, after_count = 0, 0
        if not is_multi:
            # 1. Clear database and verify
            before_count, after_count = clear_collection_manually_and_verify(db_client, collection_name)
            
            # 2. Clear all Streamlit session state
            st.session_state.processed_files = {}
            st.session_state.answer = ""
            st.session_state.retrieved_docs = []
            st.session_state.submitted_question = ""
            
            # Re-initialize vector store freshly to ensure no cached LangChain objects are reused
            vector_store = get_vector_store(db_client, embeddings, collection_name=collection_name)
            
        progress_bar = st.progress(0)
        status_placeholder = st.empty()
        
        # Create a temporary directory in workspace for processing
        temp_dir = "./temp_ingest"
        os.makedirs(temp_dir, exist_ok=True)
        
        successful_files = 0
        total_chunks_added = 0
        uploaded_filename = ""
        
        for idx, uploaded_file in enumerate(new_files_to_process):
            uploaded_filename = uploaded_file.name
            status_placeholder.markdown(f"⏳ Auto-indexing **{uploaded_file.name}**...")
            temp_file_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_file_path, "wb") as f_out:
                f_out.write(uploaded_file.getbuffer())
            
            try:
                # Read total page count
                reader = pypdf.PdfReader(temp_file_path)
                num_pages = len(reader.pages)
                
                # Ingest PDF using the newly re-created vector store
                chunks_count = ingest_pdf(temp_file_path, vector_store)
                successful_files += 1
                total_chunks_added += chunks_count
                
                # Save metadata details
                st.session_state.processed_files[uploaded_file.name] = {
                    "pages": num_pages,
                    "chunks": chunks_count,
                    "status": "success"
                }
            except Exception as e:
                st.session_state.processed_files[uploaded_file.name] = {
                    "pages": 0,
                    "chunks": 0,
                    "status": f"error: {e}"
                }
                st.error(f"Error processing {uploaded_file.name}: {e}")
                logger.error(f"Error auto-ingesting file {uploaded_file.name}: {e}")
            finally:
                if os.path.exists(temp_file_path):
                    try:
                        os.remove(temp_file_path)
                    except Exception:
                        pass
            
            progress_bar.progress((idx + 1) / len(new_files_to_process))
        
        status_placeholder.empty()
        progress_bar.empty()
        try:
            os.rmdir(temp_dir)
        except Exception:
            pass
            
        # Verify collection count after indexing (Requirement 3)
        import time
        time.sleep(0.5)
        try:
            final_count = db_client.get_collection(collection_name).points_count
        except Exception:
            final_count = 0
            
        logger.info(f"DB VERIFICATION: Vector count after indexing is {final_count}.")
        
        # 4. Log required fields after every upload (Requirement 7)
        logger.info(
            f"\n=== UPLOAD REPORT ===\n"
            f"Uploaded Filename: {uploaded_filename}\n"
            f"Collection Name: {collection_name}\n"
            f"Vectors Before Deletion: {before_count}\n"
            f"Vectors After Deletion: {after_count}\n"
            f"Vectors After Indexing: {final_count}\n"
            f"====================="
        )
        
        # Define success confirmation message
        if not is_multi:
            st.session_state.confirmation_message = "Previous knowledge base cleared. New document indexed successfully."
        else:
            st.session_state.confirmation_message = f"Successfully indexed {successful_files} file(s). Added {total_chunks_added} chunks to Qdrant!"
            
        # Trigger page rerun to render success cards and enable inputs
        st.rerun()


# Display Confirmation Banner if set
if st.session_state.confirmation_message:
    st.success(st.session_state.confirmation_message)
    st.session_state.confirmation_message = ""

# 2. Display Professional Success Indicators
if st.session_state.processed_files:
    st.markdown("### 📑 Indexed Documents")
    for fname, meta in st.session_state.processed_files.items():
        if "error" in meta["status"]:
            st.error(f"❌ **{fname}**: {meta['status']}")
        else:
            st.markdown(f"""
            <div style='background-color: #ECFDF5; border: 1px solid #10B981; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.5rem;'>
                <span style='color: #047857; font-weight: bold;'>✅ Document Indexed Successfully</span><br/>
                <span style='color: #065F46; font-size: 0.9rem;'>
                    <b>Name:</b> {fname} | <b>Pages:</b> {meta['pages']} | <b>Chunks:</b> {meta['chunks']} | <b>Status:</b> Indexed & Ready
                </span>
            </div>
            """, unsafe_allow_html=True)

# Determine if we have at least one successfully indexed document
has_indexed_docs = any("error" not in meta["status"] for meta in st.session_state.processed_files.values())

st.divider()

# 3. Chat Q&A input section
st.markdown("### 💬 Ask Questions")
if not has_indexed_docs:
    st.info("💡 Please upload one or more PDF documents above to activate the Q&A search box.")
    st.text_input(
        "Enter your question:",
        placeholder="Upload a PDF above to activate document Q&A...",
        disabled=True,
        key="disabled_question_input"
    )
else:
    # Define submit callback to handle Enter press in text_input
    def handle_query_submit():
        q = st.session_state.question_input.strip()
        if q:
            st.session_state.submitted_question = q
            st.session_state.processing = True
            # Clear previous query details
            st.session_state.answer = ""
            st.session_state.retrieved_docs = []
        # Reset input widget back to empty string
        st.session_state.question_input = ""

    # Query input field
    st.text_input(
        "Enter your question:",
        placeholder="Type your question and press Enter... (e.g. What is the main payment term?)",
        disabled=st.session_state.processing,
        key="question_input",
        on_change=handle_query_submit
    )

    # Process the query if one was submitted
    if st.session_state.submitted_question:
        question = st.session_state.submitted_question
        
        if not api_key:
            st.error("❌ OpenRouter API Key is missing. Please configure it in the sidebar.")
            st.session_state.submitted_question = ""
            st.session_state.processing = False
        elif vector_store is None:
            st.error("❌ Database connection is unavailable.")
            st.session_state.submitted_question = ""
            st.session_state.processing = False
        else:
            # Print current query debugging info to terminal before answering (Requirement 8)
            try:
                total_vecs = db_client.get_collection(collection_name).points_count
            except Exception:
                total_vecs = 0
            
            print(f"\n[QUERY SETUP] Current Collection: {collection_name} | Total Vectors: {total_vecs} | Question: {question}")
            logger.info(f"QUERY SETUP: Collection={collection_name}, Vectors={total_vecs}, Question={question}")
            
            with st.spinner("Searching documents and generating response..."):
                try:
                    # 1. Retrieve top-5 chunks
                    retrieved_docs = retrieve_context(question, vector_store, k=5)
                    st.session_state.retrieved_docs = retrieved_docs
                    
                    # Print retrieved filenames before answering (Requirement 8)
                    retrieved_filenames = list(set([doc.metadata.get("filename", "Unknown") for doc in retrieved_docs]))
                    print(f"[QUERY RETRIEVAL] Retrieved Filenames: {retrieved_filenames}")
                    logger.info(f"QUERY RETRIEVAL: Retrieved Filenames={retrieved_filenames}")


                    
                    if not retrieved_docs:
                        st.warning("No context could be retrieved for this query. The database might be empty.")
                    else:
                        # 2. Build prompt context
                        context_blocks = []
                        for doc in retrieved_docs:
                            filename = doc.metadata.get("filename", "Unknown")
                            page = doc.metadata.get("page", "Unknown")
                            context_blocks.append(f"[File: {filename}, Page: {page}]\n{doc.page_content}")
                        
                        context_text = "\n\n".join(context_blocks)
                        
                        # 3. Stream the answer using OpenRouterLLMProvider
                        st.markdown("#### 🤖 Answer:")
                        response_placeholder = st.empty()
                        full_response = ""
                        
                        llm_provider = OpenRouterLLMProvider(api_key=api_key, model_name=model_name)
                        try:
                            # Stream tokens and render
                            response_stream = llm_provider.stream_answer(question, context_text)
                            for chunk in response_stream:
                                full_response += chunk
                                response_placeholder.markdown(full_response + "▌")
                            response_placeholder.markdown(full_response)
                            st.session_state.answer = full_response
                            
                        except Exception as e:
                            st.error(f"Generation failed: {e}")
                            logger.error(f"Error during streamed QA: {e}")
                            
                except Exception as e:
                    st.error(f"An error occurred: {e}")
                    logger.error(f"Query execution failed: {e}")
                finally:
                    # Reset states to re-enable inputs
                    st.session_state.submitted_question = ""
                    st.session_state.processing = False
                    st.rerun()

    # Display persisted answer and citations from previous query on page rerun
    if st.session_state.answer or st.session_state.retrieved_docs:
        if not st.session_state.processing:  # Don't show static text if we are actively re-generating
            st.markdown("#### 🤖 Answer:")
            st.markdown(st.session_state.answer)
            
            if st.session_state.retrieved_docs:
                st.divider()
                st.markdown("#### 📑 Sources & Citations:")
                for idx, doc in enumerate(st.session_state.retrieved_docs):
                    fname = doc.metadata.get("filename", "Unknown")
                    pnum = doc.metadata.get("page", "Unknown")
                    dtype = doc.metadata.get("doc_type", "general")
                    chk_idx = doc.metadata.get("chunk_index", 0)
                    total_chks = doc.metadata.get("total_chunks", 0)
                    doc_id = doc.metadata.get("document_id", "Unknown")
                    
                    with st.expander(f"📍 Source {idx+1}: {fname} (Page {pnum})"):
                        st.markdown(f"**Document Type**: {dtype.upper()}")
                        st.markdown(f"**Chunk**: {chk_idx + 1} of {total_chks}")
                        st.markdown(f"**Document ID**: `{doc_id}`")
                        st.markdown("---")
                        st.markdown(f"*{doc.page_content}*")
