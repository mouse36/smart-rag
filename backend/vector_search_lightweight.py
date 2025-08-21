"""
Lightweight Vector Search Engine for Knowledge Base Retrieval
Uses a smaller sentence transformer model and optimized memory usage
"""

import os
import pickle
import logging
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from dataclasses import dataclass
import re
import gc

logger = logging.getLogger(__name__)

@dataclass
class DocumentChunk:
    """Represents a chunk of text from the knowledge base"""
    text: str
    source_file: str
    chunk_id: int
    metadata: Dict[str, Any]

class LightweightVectorSearchEngine:
    """Lightweight vector search engine with optimized memory usage"""
    
    def __init__(self, config):
        self.config = config
        self.model = None
        self.index = None
        self.chunks = []
        self.embeddings = None
        self._ready = False
        self._model_loaded = False
    
    def initialize(self):
        """Initialize the vector search engine with lazy loading"""
        try:
            # Only load model when actually needed
            logger.info("Vector search engine initialized (lazy loading enabled)")
            self._ready = True
            
        except Exception as e:
            logger.error(f"Failed to initialize vector search engine: {str(e)}")
            raise
    
    def _load_model_if_needed(self):
        """Load the sentence transformer model only when needed"""
        if not self._model_loaded:
            try:
                logger.info("Loading lightweight sentence transformer model...")
                from sentence_transformers import SentenceTransformer
                
                # Use a smaller model for better memory efficiency
                model_name = getattr(self.config, 'LIGHTWEIGHT_EMBEDDINGS_MODEL', 'all-MiniLM-L6-v2')
                self.model = SentenceTransformer(model_name)
                self._model_loaded = True
                
                # Force garbage collection after model loading
                gc.collect()
                
                logger.info(f"Model loaded successfully: {model_name}")
                
            except Exception as e:
                logger.error(f"Failed to load model: {str(e)}")
                raise
    
    def is_ready(self) -> bool:
        """Check if the vector search engine is ready"""
        return self._ready
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant passages given a query"""
        if not self.is_ready():
            raise RuntimeError("Vector search engine not initialized")
        
        try:
            # Load model and data if not already loaded
            self._load_model_if_needed()
            
            # Load cached data if not already loaded
            if not self.chunks or self.index is None:
                if not self._load_cached_data():
                    logger.warning("No cached data found. Vector search unavailable.")
                    return []
            
            # Generate query embedding
            query_embedding = self.model.encode([query])
            
            # Import FAISS only when needed
            import faiss
            
            # Search using FAISS
            scores, indices = self.index.search(query_embedding.astype(np.float32), top_k)
            
            # Format results
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx == -1:  # FAISS returns -1 for invalid indices
                    continue
                
                chunk = self.chunks[idx]
                results.append({
                    'text': chunk.text,
                    'source_file': chunk.source_file,
                    'chunk_id': chunk.chunk_id,
                    'similarity_score': float(score),
                    'metadata': chunk.metadata
                })
            
            logger.debug(f"Found {len(results)} relevant passages for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error during vector search: {str(e)}")
            return []
    
    def _load_cached_data(self) -> bool:
        """Load cached embeddings and index"""
        try:
            if (os.path.exists(self.config.EMBEDDINGS_CACHE_PATH) and 
                os.path.exists(self.config.INDEX_CACHE_PATH)):
                
                logger.info("Loading cached embeddings and index...")
                
                # Load embeddings and chunks
                with open(self.config.EMBEDDINGS_CACHE_PATH, 'rb') as f:
                    data = pickle.load(f)
                    self.chunks = data['chunks']
                    self.embeddings = data['embeddings']
                
                # Load FAISS index
                import faiss
                self.index = faiss.read_index(self.config.INDEX_CACHE_PATH)
                
                logger.info(f"Loaded {len(self.chunks)} chunks from cache")
                return True
            
        except Exception as e:
            logger.warning(f"Failed to load cached data: {str(e)}")
        
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector search engine"""
        if not self.is_ready():
            return {'status': 'not_ready'}
        
        return {
            'status': 'ready',
            'model_loaded': self._model_loaded,
            'total_chunks': len(self.chunks) if self.chunks else 0,
            'vector_dimension': getattr(self.config, 'LIGHTWEIGHT_VECTOR_DIMENSION', 384),
            'model_name': getattr(self.config, 'LIGHTWEIGHT_EMBEDDINGS_MODEL', 'all-MiniLM-L6-v2'),
            'chunk_size': self.config.CHUNK_SIZE,
            'chunk_overlap': self.config.CHUNK_OVERLAP
        }

class SimpleKeywordSearchEngine:
    """Simple keyword-based search as fallback when vector search is unavailable"""
    
    def __init__(self, config):
        self.config = config
        self.chunks = []
        self._ready = False
    
    def initialize(self):
        """Initialize the keyword search engine"""
        try:
            logger.info("Initializing simple keyword search engine...")
            self._load_chunks()
            self._ready = True
            logger.info(f"Keyword search engine initialized with {len(self.chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Failed to initialize keyword search engine: {str(e)}")
            raise
    
    def _load_chunks(self):
        """Load document chunks from cache or process files"""
        try:
            # Try to load from cache first
            if os.path.exists(self.config.EMBEDDINGS_CACHE_PATH):
                with open(self.config.EMBEDDINGS_CACHE_PATH, 'rb') as f:
                    data = pickle.load(f)
                    self.chunks = data['chunks']
                logger.info(f"Loaded {len(self.chunks)} chunks from cache")
                return
            
            # If no cache, process files (simplified version)
            logger.warning("No cached chunks found. Keyword search will be limited.")
            self.chunks = []
            
        except Exception as e:
            logger.error(f"Error loading chunks: {str(e)}")
            self.chunks = []
    
    def is_ready(self) -> bool:
        """Check if the keyword search engine is ready"""
        return self._ready
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant passages using keyword matching"""
        if not self.is_ready():
            return []
        
        try:
            # Simple keyword matching
            query_terms = set(query.lower().split())
            results = []
            
            for chunk in self.chunks:
                chunk_text_lower = chunk.text.lower()
                matches = sum(1 for term in query_terms if term in chunk_text_lower)
                
                if matches > 0:
                    # Simple scoring based on term frequency
                    score = matches / len(query_terms)
                    results.append({
                        'text': chunk.text,
                        'source_file': chunk.source_file,
                        'chunk_id': chunk.chunk_id,
                        'similarity_score': score,
                        'metadata': chunk.metadata
                    })
            
            # Sort by score and return top_k
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Error during keyword search: {str(e)}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the keyword search engine"""
        if not self.is_ready():
            return {'status': 'not_ready'}
        
        return {
            'status': 'ready',
            'search_type': 'keyword',
            'total_chunks': len(self.chunks),
            'chunk_size': self.config.CHUNK_SIZE,
            'chunk_overlap': self.config.CHUNK_OVERLAP
        }
