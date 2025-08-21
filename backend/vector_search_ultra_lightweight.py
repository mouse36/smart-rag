"""
Ultra-Lightweight Vector Search Engine for Memory-Constrained Environments
Uses scikit-learn instead of FAISS and aggressive memory management
"""

import os
import pickle
import logging
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from dataclasses import dataclass
import re
import gc
import psutil
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)

@dataclass
class DocumentChunk:
    """Represents a chunk of text from the knowledge base"""
    text: str
    source_file: str
    chunk_id: int
    metadata: Dict[str, Any]

class UltraLightweightVectorSearchEngine:
    """Ultra-lightweight vector search engine for memory-constrained environments"""
    
    def __init__(self, config):
        self.config = config
        self.model = None
        self.chunks = []
        self.embeddings = None
        self.tfidf_vectorizer = None
        self.tfidf_matrix = None
        self._ready = False
        self._model_loaded = False
        self._chunks_loaded = False
        
        # Ultra-conservative memory settings for Render free tier
        self.max_memory_mb = int(os.getenv('MAX_MEMORY_MB', 300))  # Very conservative
        self.use_tfidf_fallback = os.getenv('USE_TFIDF_FALLBACK', 'True').lower() == 'true'
        self.min_memory_for_model = int(os.getenv('MIN_MEMORY_FOR_MODEL', 100))  # Lower threshold
    
    def initialize(self):
        """Initialize the ultra-lightweight vector search engine"""
        try:
            logger.info("Initializing ultra-lightweight vector search engine...")
            
            # Check available memory
            available_memory = psutil.virtual_memory().available / (1024 * 1024)  # MB
            logger.info(f"Available memory: {available_memory:.1f} MB")
            
            # Always try to load chunks first - they're essential for RAG
            if self._load_cached_data():
                logger.info("Loaded cached data")
                self._chunks_loaded = True
                self._ready = True
                return
            
            # If no cache, we must process the knowledge base
            logger.info("No cached data found. Processing knowledge base...")
            
            # Check if we have enough memory to process
            if available_memory < 80:  # Need at least 80MB to process files
                logger.error(f"Insufficient memory ({available_memory:.1f} MB) to process knowledge base")
                raise RuntimeError("Insufficient memory to process knowledge base")
            
            # Process knowledge base with ultra-conservative memory management
            self._process_knowledge_base_ultra_lightweight()
            
            # Save cache for future use
            if self.chunks:  # Only save if we successfully loaded chunks
                self._save_cached_data()
                self._chunks_loaded = True
            
            self._ready = True
            logger.info(f"Ultra-lightweight vector search engine initialized with {len(self.chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Failed to initialize ultra-lightweight vector search engine: {str(e)}")
            # Only mark as ready if we have chunks loaded
            if self.chunks:
                self._ready = True
                self._chunks_loaded = True
                logger.warning("Vector search failed, but chunks are available for keyword search")
            else:
                raise  # Re-raise if we can't even load chunks
    
    def _load_model_if_needed(self):
        """Load the sentence transformer model only when needed"""
        if not self._model_loaded:
            try:
                # Check memory before loading
                available_memory = psutil.virtual_memory().available / (1024 * 1024)
                if available_memory < self.min_memory_for_model:
                    logger.warning(f"Insufficient memory ({available_memory:.1f} MB) for model loading. Using TF-IDF fallback.")
                    return False
                
                logger.info("Loading ultra-lightweight sentence transformer model...")
                from sentence_transformers import SentenceTransformer
                
                # Use the smallest available model
                model_name = 'all-MiniLM-L6-v2'  # 384 dimensions, very small
                self.model = SentenceTransformer(model_name)
                
                # Force garbage collection after model loading
                gc.collect()
                
                self._model_loaded = True
                logger.info("Ultra-lightweight sentence transformer model loaded successfully")
                return True
                
            except Exception as e:
                logger.error(f"Failed to load sentence transformer model: {str(e)}")
                return False
        
        return True
    
    def _process_knowledge_base_ultra_lightweight(self):
        """Process knowledge base with ultra-conservative memory management"""
        try:
            logger.info("Processing knowledge base with ultra-lightweight approach...")
            
            # Load and process files one by one to minimize memory usage
            knowledge_base_path = self.config.KNOWLEDGE_BASE_PATH
            if not os.path.exists(knowledge_base_path):
                logger.error(f"Knowledge base path does not exist: {knowledge_base_path}")
                return
            
            files = [f for f in os.listdir(knowledge_base_path) if f.endswith('.txt')]
            logger.info(f"Found {len(files)} knowledge base files")
            
            all_chunks = []
            chunk_id = 0
            
            for filename in files:
                try:
                    file_path = os.path.join(knowledge_base_path, filename)
                    
                    # Read file in chunks to minimize memory usage
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Split into smaller chunks for better memory efficiency
                    chunk_size = min(self.config.CHUNK_SIZE, 300)  # Smaller chunks
                    overlap = min(self.config.CHUNK_OVERLAP, 30)   # Smaller overlap
                    
                    chunks = self._split_text_into_chunks(content, chunk_size, overlap)
                    
                    for i, chunk_text in enumerate(chunks):
                        if chunk_text.strip():  # Only add non-empty chunks
                            chunk = DocumentChunk(
                                text=chunk_text.strip(),
                                source_file=filename,
                                chunk_id=chunk_id,
                                metadata={
                                    'file': filename,
                                    'chunk_index': i,
                                    'chunk_size': len(chunk_text)
                                }
                            )
                            all_chunks.append(chunk)
                            chunk_id += 1
                    
                    # Force garbage collection after each file
                    gc.collect()
                    
                    # Check memory usage
                    available_memory = psutil.virtual_memory().available / (1024 * 1024)
                    if available_memory < 50:  # Very conservative threshold
                        logger.warning(f"Low memory ({available_memory:.1f} MB) after processing {filename}")
                        break
                        
                except Exception as e:
                    logger.error(f"Error processing file {filename}: {str(e)}")
                    continue
            
            self.chunks = all_chunks
            logger.info(f"Processed {len(self.chunks)} chunks from knowledge base")
            
            # Try to create embeddings if we have enough memory
            if self.chunks and self._load_model_if_needed():
                self._create_embeddings_ultra_lightweight()
            elif self.chunks and self.use_tfidf_fallback:
                self._create_tfidf_index()
            
        except Exception as e:
            logger.error(f"Error processing knowledge base: {str(e)}")
            raise
    
    def _create_embeddings_ultra_lightweight(self):
        """Create embeddings with ultra-conservative memory management"""
        try:
            logger.info("Creating embeddings with ultra-lightweight approach...")
            
            if not self.model:
                logger.warning("No model available for embeddings")
                return
            
            # Process embeddings in batches to minimize memory usage
            batch_size = 10  # Very small batch size
            all_embeddings = []
            
            for i in range(0, len(self.chunks), batch_size):
                batch_chunks = self.chunks[i:i + batch_size]
                batch_texts = [chunk.text for chunk in batch_chunks]
                
                # Create embeddings for batch
                batch_embeddings = self.model.encode(batch_texts, show_progress_bar=False)
                all_embeddings.append(batch_embeddings)
                
                # Force garbage collection after each batch
                gc.collect()
                
                # Check memory usage
                available_memory = psutil.virtual_memory().available / (1024 * 1024)
                if available_memory < 30:  # Very conservative threshold
                    logger.warning(f"Low memory ({available_memory:.1f} MB) during embedding creation")
                    break
            
            if all_embeddings:
                self.embeddings = np.vstack(all_embeddings)
                logger.info(f"Created embeddings for {len(self.embeddings)} chunks")
            
        except Exception as e:
            logger.error(f"Error creating embeddings: {str(e)}")
            # Fall back to TF-IDF if embeddings fail
            if self.use_tfidf_fallback:
                self._create_tfidf_index()
    
    def _create_tfidf_index(self):
        """Create TF-IDF index as a lightweight alternative to embeddings"""
        try:
            logger.info("Creating TF-IDF index as lightweight alternative...")
            
            texts = [chunk.text for chunk in self.chunks]
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=1000,  # Limit features to save memory
                stop_words='english',
                ngram_range=(1, 2),
                min_df=2,
                max_df=0.95
            )
            
            self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            logger.info(f"Created TF-IDF index with {self.tfidf_matrix.shape[1]} features")
            
        except Exception as e:
            logger.error(f"Error creating TF-IDF index: {str(e)}")
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant documents using ultra-lightweight approach"""
        if not self._ready or not self.chunks:
            logger.warning("Vector search engine not ready")
            return []
        
        try:
            # Try semantic search first if embeddings are available
            if self.embeddings is not None and self.model:
                return self._semantic_search(query, top_k)
            elif self.tfidf_matrix is not None:
                return self._tfidf_search(query, top_k)
            else:
                # Fallback to keyword search
                return self._keyword_search(query, top_k)
                
        except Exception as e:
            logger.error(f"Error in search: {str(e)}")
            # Fallback to keyword search
            return self._keyword_search(query, top_k)
    
    def _semantic_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Perform semantic search using embeddings"""
        try:
            # Encode query
            query_embedding = self.model.encode([query])
            
            # Calculate similarities using scikit-learn (more memory efficient than FAISS)
            similarities = cosine_similarity(query_embedding, self.embeddings)[0]
            
            # Get top k results
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            results = []
            for idx in top_indices:
                if similarities[idx] > 0.1:  # Minimum similarity threshold
                    results.append({
                        'text': self.chunks[idx].text,
                        'source_file': self.chunks[idx].source_file,
                        'similarity': float(similarities[idx]),
                        'metadata': self.chunks[idx].metadata
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            return []
    
    def _tfidf_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Perform search using TF-IDF"""
        try:
            # Transform query
            query_vector = self.tfidf_vectorizer.transform([query])
            
            # Calculate similarities
            similarities = cosine_similarity(query_vector, self.tfidf_matrix)[0]
            
            # Get top k results
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            results = []
            for idx in top_indices:
                if similarities[idx] > 0.01:  # Lower threshold for TF-IDF
                    results.append({
                        'text': self.chunks[idx].text,
                        'source_file': self.chunks[idx].source_file,
                        'similarity': float(similarities[idx]),
                        'metadata': self.chunks[idx].metadata
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in TF-IDF search: {str(e)}")
            return []
    
    def _keyword_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Fallback keyword search"""
        try:
            query_terms = query.lower().split()
            results = []
            
            for chunk in self.chunks:
                chunk_text_lower = chunk.text.lower()
                score = sum(1 for term in query_terms if term in chunk_text_lower)
                
                if score > 0:
                    results.append({
                        'text': chunk.text,
                        'source_file': chunk.source_file,
                        'similarity': score / len(query_terms),
                        'metadata': chunk.metadata
                    })
            
            # Sort by score and return top k
            results.sort(key=lambda x: x['similarity'], reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Error in keyword search: {str(e)}")
            return []
    
    def _split_text_into_chunks(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Split text into overlapping chunks"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundaries
            if end < len(text):
                # Look for sentence endings
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
    
    def _load_cached_data(self) -> bool:
        """Load cached embeddings and index"""
        try:
            cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
            chunks_cache_path = os.path.join(cache_dir, 'chunks.pkl')
            
            if os.path.exists(chunks_cache_path):
                with open(chunks_cache_path, 'rb') as f:
                    self.chunks = pickle.load(f)
                logger.info(f"Loaded {len(self.chunks)} chunks from cache")
                
                # Try to load embeddings if available
                embeddings_cache_path = os.path.join(cache_dir, 'embeddings_ultra.pkl')
                if os.path.exists(embeddings_cache_path):
                    with open(embeddings_cache_path, 'rb') as f:
                        self.embeddings = pickle.load(f)
                    logger.info("Loaded embeddings from cache")
                    return True
                
                # Try to load TF-IDF if available
                tfidf_cache_path = os.path.join(cache_dir, 'tfidf_ultra.pkl')
                if os.path.exists(tfidf_cache_path):
                    with open(tfidf_cache_path, 'rb') as f:
                        cache_data = pickle.load(f)
                        self.tfidf_vectorizer = cache_data['vectorizer']
                        self.tfidf_matrix = cache_data['matrix']
                    logger.info("Loaded TF-IDF index from cache")
                    return True
                
                return True  # At least chunks are loaded
            
            return False
            
        except Exception as e:
            logger.error(f"Error loading cached data: {str(e)}")
            return False
    
    def _save_cached_data(self):
        """Save embeddings and index to cache"""
        try:
            cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
            os.makedirs(cache_dir, exist_ok=True)
            
            # Save chunks
            chunks_cache_path = os.path.join(cache_dir, 'chunks.pkl')
            with open(chunks_cache_path, 'wb') as f:
                pickle.dump(self.chunks, f)
            
            # Save embeddings if available
            if self.embeddings is not None:
                embeddings_cache_path = os.path.join(cache_dir, 'embeddings_ultra.pkl')
                with open(embeddings_cache_path, 'wb') as f:
                    pickle.dump(self.embeddings, f)
            
            # Save TF-IDF if available
            if self.tfidf_matrix is not None and self.tfidf_vectorizer is not None:
                tfidf_cache_path = os.path.join(cache_dir, 'tfidf_ultra.pkl')
                with open(tfidf_cache_path, 'wb') as f:
                    pickle.dump({
                        'vectorizer': self.tfidf_vectorizer,
                        'matrix': self.tfidf_matrix
                    }, f)
            
            logger.info("Cached data saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving cached data: {str(e)}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the vector search engine"""
        return {
            'ready': self._ready,
            'chunks_loaded': self._chunks_loaded,
            'model_loaded': self._model_loaded,
            'num_chunks': len(self.chunks),
            'embeddings_available': self.embeddings is not None,
            'tfidf_available': self.tfidf_matrix is not None,
            'memory_usage_mb': psutil.virtual_memory().used / (1024 * 1024)
        }
