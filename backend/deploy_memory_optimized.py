#!/usr/bin/env python3
"""
Deployment Memory Optimization Script
Pre-processes knowledge base to reduce memory usage during startup
"""

import os
import sys
import pickle
import logging
from pathlib import Path

# Add the backend directory to the path
sys.path.append(os.path.dirname(__file__))

from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def preprocess_knowledge_base():
    """Pre-process knowledge base to create optimized cache files"""
    try:
        config = Config()
        knowledge_base_path = config.KNOWLEDGE_BASE_PATH
        cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
        
        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)
        
        logger.info(f"Pre-processing knowledge base from: {knowledge_base_path}")
        
        if not os.path.exists(knowledge_base_path):
            logger.error(f"Knowledge base path does not exist: {knowledge_base_path}")
            return False
        
        # Get all text files
        files = [f for f in os.listdir(knowledge_base_path) if f.endswith('.txt')]
        logger.info(f"Found {len(files)} knowledge base files")
        
        # Process files and create chunks
        all_chunks = []
        chunk_id = 0
        
        for filename in files:
            try:
                file_path = os.path.join(knowledge_base_path, filename)
                logger.info(f"Processing: {filename}")
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Split into smaller chunks
                chunk_size = 300  # Smaller chunks for memory efficiency
                overlap = 30
                
                chunks = split_text_into_chunks(content, chunk_size, overlap)
                
                for i, chunk_text in enumerate(chunks):
                    if chunk_text.strip():
                        chunk = {
                            'text': chunk_text.strip(),
                            'source_file': filename,
                            'chunk_id': chunk_id,
                            'metadata': {
                                'file': filename,
                                'chunk_index': i,
                                'chunk_size': len(chunk_text)
                            }
                        }
                        all_chunks.append(chunk)
                        chunk_id += 1
                
            except Exception as e:
                logger.error(f"Error processing file {filename}: {str(e)}")
                continue
        
        # Save chunks to cache
        chunks_cache_path = os.path.join(cache_dir, 'chunks.pkl')
        with open(chunks_cache_path, 'wb') as f:
            pickle.dump(all_chunks, f)
        
        logger.info(f"Saved {len(all_chunks)} chunks to cache")
        
        # Create a simple TF-IDF index for lightweight search
        create_tfidf_index(all_chunks, cache_dir)
        
        return True
        
    except Exception as e:
        logger.error(f"Error in pre-processing: {str(e)}")
        return False

def split_text_into_chunks(text: str, chunk_size: int, overlap: int):
    """Split text into overlapping chunks"""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundaries
        if end < len(text):
            for i in range(end, max(start + chunk_size - 100, start), -1):
                if text[i] in '.!?':
                    end = i + 1
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks

def create_tfidf_index(chunks, cache_dir):
    """Create a simple TF-IDF index for lightweight search"""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        
        texts = [chunk['text'] for chunk in chunks]
        
        vectorizer = TfidfVectorizer(
            max_features=1000,  # Limit features to save memory
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.95
        )
        
        matrix = vectorizer.fit_transform(texts)
        
        # Save TF-IDF index
        tfidf_cache_path = os.path.join(cache_dir, 'tfidf_ultra.pkl')
        with open(tfidf_cache_path, 'wb') as f:
            pickle.dump({
                'vectorizer': vectorizer,
                'matrix': matrix
            }, f)
        
        logger.info(f"Created TF-IDF index with {matrix.shape[1]} features")
        
    except Exception as e:
        logger.error(f"Error creating TF-IDF index: {str(e)}")

def main():
    """Main function"""
    logger.info("Starting knowledge base pre-processing...")
    
    success = preprocess_knowledge_base()
    
    if success:
        logger.info("Knowledge base pre-processing completed successfully")
        return 0
    else:
        logger.error("Knowledge base pre-processing failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
