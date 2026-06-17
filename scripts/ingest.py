import os
import argparse
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb
from llama_index.core.node_parser import SentenceSplitter

def get_metadata(filename: str):
    """
    Extract metadata from the file path.
    Assuming the directory structure is data/{persona}/{topic}/file.txt
    """
    parts = os.path.normpath(filename).split(os.sep)
    metadata = {}
    try:
        data_idx = parts.index("data")
        if len(parts) > data_idx + 1:
            metadata["persona"] = parts[data_idx + 1]
        if len(parts) > data_idx + 2:
            metadata["topic"] = parts[data_idx + 2]
    except ValueError:
        pass
    return metadata

def ingest_data(data_dir: str = "./data", db_path: str = "./chroma_db"):
    print(f"Starting ingestion from {data_dir}...")
    
    # Ensure data directory exists
    os.makedirs(data_dir, exist_ok=True)
    
    # Initialize Chroma client and collection
    db = chromadb.PersistentClient(path=db_path)
    chroma_collection = db.get_or_create_collection("portfolio_builders")

    # Assign chroma as the vector store to the context
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # Load documents with metadata
    try:
        documents = SimpleDirectoryReader(
            input_dir=data_dir, 
            recursive=True, 
            file_metadata=get_metadata,
            required_exts=[".txt", ".pdf", ".md", ".csv"]
        ).load_data()
    except ValueError as e:
        print(f"Error loading documents: {e}")
        print(f"Please place some documents in the {data_dir} directory.")
        return

    if not documents:
        print(f"No documents found in {data_dir} directory.")
        return

    # Parse into nodes (chunking the text)
    parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)
    nodes = parser.get_nodes_from_documents(documents)

    print(f"Loaded {len(documents)} documents and parsed into {len(nodes)} chunks.")

    # Create index and embeddings (This requires OPENAI_API_KEY by default or another embedding model)
    index = VectorStoreIndex(
        nodes, 
        storage_context=storage_context,
        show_progress=True
    )
    print(f"Ingestion complete. Vector store created/updated at {db_path}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest documents into ChromaDB using LlamaIndex.")
    parser.add_argument("--data-dir", type=str, default="./data", help="Path to the data directory.")
    parser.add_argument("--db-path", type=str, default="./chroma_db", help="Path to store the ChromaDB.")
    args = parser.parse_args()
    
    ingest_data(data_dir=args.data_dir, db_path=args.db_path)
