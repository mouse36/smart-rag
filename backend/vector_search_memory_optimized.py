"""
Memory-Optimized Vector Search Engine for Knowledge Base Retrieval
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
import psutil

logger = logging.getLogger(__name__)

@dataclass
class DocumentChunk:
    """Represents a chunk of text from the knowledge base"""
    text: str
    source_file: str
    chunk_id: int
    metadata: Dict[str, Any]

class MemoryOptimizedVectorSearchEngine:
    """Memory-optimized vector search engine with smaller model and better memory management"""
    
    def __init__(self, config):
        self.config = config
        self.model = None
        self.index = None
        self.chunks = []
        self.embeddings = None
        self._ready = False
        self._model_loaded = False
        
        # Memory optimization settings
        self.max_memory_mb = int(os.getenv('MAX_MEMORY_MB', 512))
        self.use_smaller_model = os.getenv('USE_SMALLER_MODEL', 'True').lower() == 'true'
    
    def initialize(self):
        """Initialize the vector search engine with memory optimization"""
        try:
            logger.info("Initializing memory-optimized vector search engine...")
            
            # Check available memory
            available_memory = psutil.virtual_memory().available / (1024 * 1024)  # MB
            logger.info(f"Available memory: {available_memory:.1f} MB")
            
            if available_memory < self.max_memory_mb:
                logger.warning(f"Low memory detected ({available_memory:.1f} MB). Using fallback search.")
                self._ready = True
                return
            
            # Try to load cached data first
            if self._load_cached_data():
                logger.info("Loaded cached embeddings and index")
                self._ready = True
                return
            
            # If no cache, process knowledge base with memory monitoring
            logger.info("No cached data found. Processing knowledge base...")
            self._process_knowledge_base_memory_optimized()
            self._save_cached_data()
            
            self._ready = True
            logger.info(f"Vector search engine initialized with {len(self.chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector search engine: {str(e)}")
            # Don't raise - allow fallback to keyword search
            self._ready = True
    
    def _load_model_if_needed(self):
        """Load the sentence transformer model only when needed"""
        if not self._model_loaded:
            try:
                # Check memory before loading
                available_memory = psutil.virtual_memory().available / (1024 * 1024)
                if available_memory < 200:  # Need at least 200MB for model
                    logger.warning(f"Insufficient memory ({available_memory:.1f} MB) for model loading")
                    return False
                
                logger.info("Loading memory-optimized sentence transformer model...")
                from sentence_transformers import SentenceTransformer
                
                # Use a smaller model for better memory efficiency
                if self.use_smaller_model:
                    model_name = 'all-MiniLM-L6-v2'  # 384 dimensions, ~90MB
                else:
                    model_name = self.config.EMBEDDINGS_MODEL
                
                self.model = SentenceTransformer(model_name)
                self._model_loaded = True
                
                # Force garbage collection after model loading
                gc.collect()
                
                logger.info(f"Model loaded successfully: {model_name}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to load model: {str(e)}")
                return False
        
        return True
    
    def is_ready(self) -> bool:
        """Check if the vector search engine is ready"""
        return self._ready
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant passages given a query"""
        if not self.is_ready():
            return []
        
        try:
            # Try vector search first
            if self._load_model_if_needed() and self.index is not None:
                return self._vector_search(query, top_k)
            else:
                # Fallback to keyword search
                logger.info("Falling back to keyword search")
                return self._keyword_search(query, top_k)
            
        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            # Fallback to keyword search
            return self._keyword_search(query, top_k)
    
    def _vector_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Perform vector search"""
        try:
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
            
            logger.debug(f"Vector search found {len(results)} relevant passages")
            return results
            
        except Exception as e:
            logger.error(f"Error during vector search: {str(e)}")
            return []
    
    def _keyword_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Fallback keyword search"""
        try:
            query_terms = set(query.lower().split())
            results = []
            
            for chunk in self.chunks:
                chunk_text_lower = chunk.text.lower()
                matches = sum(1 for term in query_terms if term in chunk_text_lower)
                
                if matches > 0:
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
            logger.debug(f"Keyword search found {len(results)} relevant passages")
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Error during keyword search: {str(e)}")
            return []
    
    def _process_knowledge_base_memory_optimized(self):
        """Process knowledge base with memory monitoring"""
        knowledge_base_path = self.config.KNOWLEDGE_BASE_PATH
        
        if not os.path.exists(knowledge_base_path):
            raise FileNotFoundError(f"Knowledge base path not found: {knowledge_base_path}")
        
        self.chunks = []
        all_texts = []
        
        # Process files in smaller batches to manage memory
        files = [f for f in os.listdir(knowledge_base_path) if f.endswith('.txt')]
        batch_size = 5  # Process 5 files at a time
        
        for i in range(0, len(files), batch_size):
            batch_files = files[i:i + batch_size]
            
            # Check memory before processing batch
            available_memory = psutil.virtual_memory().available / (1024 * 1024)
            if available_memory < 100:  # Need at least 100MB
                logger.warning(f"Low memory during processing ({available_memory:.1f} MB). Stopping.")
                break
            
            for filename in batch_files:
                file_path = os.path.join(knowledge_base_path, filename)
                logger.info(f"Processing file: {filename}")
                
                try:
                    chunks = self._process_file(file_path, filename)
                    self.chunks.extend(chunks)
                    all_texts.extend([chunk.text for chunk in chunks])
                    
                except Exception as e:
                    logger.error(f"Error processing file {filename}: {str(e)}")
                    continue
            
            # Force garbage collection after each batch
            gc.collect()
        
        if not all_texts:
            raise ValueError("No text content found in knowledge base")
        
        # Load model and generate embeddings
        if self._load_model_if_needed():
            logger.info(f"Generating embeddings for {len(all_texts)} chunks...")
            self.embeddings = self.model.encode(all_texts, show_progress_bar=True)
            
            # Create FAISS index
            logger.info("Creating FAISS index...")
            import faiss
            self.index = faiss.IndexFlatIP(self.config.VECTOR_DIMENSION)
            
            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(self.embeddings)
            self.index.add(self.embeddings.astype(np.float32))
            
            logger.info(f"Successfully processed {len(self.chunks)} chunks")
        else:
            logger.warning("Could not load model. Only keyword search will be available.")
    
    def _process_file(self, file_path: str, filename: str) -> List[DocumentChunk]:
        """Process a single file and return chunks"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Clean and chunk the content
            chunks = self._chunk_text(content, filename)
            return chunks
            
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            return []
    
    def _chunk_text(self, text: str, source_file: str) -> List[DocumentChunk]:
        """Split text into chunks with overlap"""
        # Clean the text
        text = self._clean_text(text)
        
        # Split into sentences for better chunking
        sentences = self._split_into_sentences(text)
        
        chunks = []
        chunk_id = 0
        current_chunk = ""
        current_sentences = []
        
        for sentence in sentences:
            # Check if adding this sentence would exceed chunk size
            potential_chunk = current_chunk + " " + sentence if current_chunk else sentence
            
            if len(potential_chunk) <= self.config.CHUNK_SIZE:
                current_chunk = potential_chunk
                current_sentences.append(sentence)
            else:
                # Save current chunk if it's not empty
                if current_chunk:
                    chunks.append(DocumentChunk(
                        text=current_chunk.strip(),
                        source_file=source_file,
                        chunk_id=chunk_id,
                        metadata={
                            'sentence_count': len(current_sentences),
                            'char_count': len(current_chunk)
                        }
                    ))
                    chunk_id += 1
                
                # Start new chunk with overlap
                overlap_sentences = current_sentences[-self._calculate_overlap_sentences():]
                current_chunk = " ".join(overlap_sentences + [sentence])
                current_sentences = overlap_sentences + [sentence]
        
        # Don't forget the last chunk
        if current_chunk:
            chunks.append(DocumentChunk(
                text=current_chunk.strip(),
                source_file=source_file,
                chunk_id=chunk_id,
                metadata={
                    'sentence_count': len(current_sentences),
                    'char_count': len(current_chunk)
                }
            ))
        
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that might interfere with processing
        text = re.sub(r'[^\w\s\.,!?;:()\-"\']+', ' ', text)
        
        # Normalize quotes
        text = re.sub(r'["""]', '"', text)
        text = re.sub(r"[''']", "'", text)
        
        return text.strip()
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting based on punctuation
        sentences = re.split(r'[.!?]+\s+', text)
        
        # Filter out very short sentences and clean
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        return sentences
    
    def _calculate_overlap_sentences(self) -> int:
        """Calculate number of sentences to overlap based on config"""
        # Estimate average sentence length and calculate overlap
        avg_sentence_length = 80  # rough estimate
        overlap_sentences = max(1, self.config.CHUNK_OVERLAP // avg_sentence_length)
        return min(overlap_sentences, 3)  # Cap at 3 sentences
    
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
    
    def _save_cached_data(self):
        """Save embeddings and index to cache"""
        try:
            if self.embeddings is not None and self.index is not None:
                # Save embeddings and chunks
                with open(self.config.EMBEDDINGS_CACHE_PATH, 'wb') as f:
                    pickle.dump({
                        'chunks': self.chunks,
                        'embeddings': self.embeddings
                    }, f)
                
                # Save FAISS index
                import faiss
                faiss.write_index(self.index, self.config.INDEX_CACHE_PATH)
                
                logger.info("Cached embeddings and index saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save cached data: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector search engine"""
        if not self.is_ready():
            return {'status': 'not_ready'}
        
        return {
            'status': 'ready',
            'model_loaded': self._model_loaded,
            'total_chunks': len(self.chunks),
            'vector_dimension': self.config.VECTOR_DIMENSION,
            'model_name': self.config.EMBEDDINGS_MODEL,
            'chunk_size': self.config.CHUNK_SIZE,
            'chunk_overlap': self.config.CHUNK_OVERLAP,
            'search_type': 'vector' if self._model_loaded and self.index else 'keyword'
        }
