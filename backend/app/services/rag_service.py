import os
import chromadb
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Configure HuggingFace local embedding model globally in LlamaIndex Settings
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
# We set LLM to None in Settings since we use Groq API directly in main.py
Settings.llm = None

# Resolve paths relative to workspace root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "chroma_db")

class RAGService:
    def __init__(self):
        self.db_path = DB_PATH
        self.collection_name = "portfolio_builders"
        self._init_index()

    def _init_index(self):
        """Initialize ChromaDB client, collection, and LlamaIndex VectorStoreIndex."""
        try:
            self.db = chromadb.PersistentClient(path=self.db_path)
            self.chroma_collection = self.db.get_or_create_collection(self.collection_name)
            self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
            self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
            
            # Load index from vector store
            self.index = VectorStoreIndex.from_vector_store(
                vector_store=self.vector_store,
                storage_context=self.storage_context
            )
        except Exception as e:
            print(f"Error initializing RAG index: {e}")
            self.index = None

    def query_context(self, query_text: str, category_filter: str = None, top_k: int = 3) -> str:
        """
        Query ChromaDB for relevant document chunks.
        Optionally filter by metadata category (e.g. 'courses' or 'general').
        """
        if not self.index:
            return ""
        
        try:
            # Check if index has nodes
            # If the database is empty, return empty context
            if self.chroma_collection.count() == 0:
                print("Chroma collection is empty.")
                return ""

            # Define vector store retriever
            retriever = self.index.as_retriever(similarity_top_k=top_k)
            
            # Retrieve nodes
            nodes = retriever.retrieve(query_text)
            
            # Apply category filtering manually if specified
            relevant_chunks = []
            for node in nodes:
                metadata = node.node.metadata or {}
                # Filter by category if filter is active
                if category_filter and metadata.get("category") != category_filter:
                    continue
                relevant_chunks.append(node.node.text)

            # Fallback to no category filter if filter cleared out all matches
            if not relevant_chunks and nodes:
                relevant_chunks = [node.node.text for node in nodes]
                
            return "\n\n".join(relevant_chunks[:top_k])
        except Exception as e:
            print(f"Error querying RAG context: {e}")
            return ""

# Singleton instance
rag_service = RAGService()
