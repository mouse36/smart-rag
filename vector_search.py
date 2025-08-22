"""
Vector Search Engine for Knowledge Base Retrieval
Uses sentence-transformers for embeddings and scikit-learn for efficient similarity search
"""

import os
import pickle
import logging
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import normalize
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)

@dataclass
class DocumentChunk:
    """Represents a chunk of text from the knowledge base"""
    text: str
    source_file: str
    chunk_id: int
    metadata: Dict[str, Any]

class VectorSearchEngine:
    """Handles vector embeddings generation and similarity search using scikit-learn"""
    
    def __init__(self, config):
        self.config = config
        self.model = None
        self.nearest_neighbors = None
        self.chunks = []
        self.embeddings = None
        self._ready = False
    
    def initialize(self):
        """Initialize the vector search engine"""
        try:
            logger.info("Loading sentence transformer model...")
            self.model = SentenceTransformer(self.config.EMBEDDINGS_MODEL)
            
            # Try to load cached embeddings and index
            if self._load_cached_data():
                logger.info("Loaded cached embeddings and index")
            else:
                logger.info("No cached data found. Processing knowledge base...")
                self._process_knowledge_base()
                self._save_cached_data()
            
            self._ready = True
            logger.info(f"Vector search engine initialized with {len(self.chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector search engine: {str(e)}")
            raise
    
    def is_ready(self) -> bool:
        """Check if the vector search engine is ready"""
        return self._ready and self.model is not None and self.nearest_neighbors is not None
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant passages given a query using scikit-learn"""
        if not self.is_ready():
            raise RuntimeError("Vector search engine not initialized")
        
        try:
            # Generate query embedding
            query_embedding = self.model.encode([query])
            
            # Normalize query embedding for cosine similarity
            query_embedding_normalized = normalize(query_embedding.reshape(1, -1))
            
            # Search using scikit-learn NearestNeighbors
            distances, indices = self.nearest_neighbors.kneighbors(
                query_embedding_normalized, 
                n_neighbors=min(top_k, len(self.chunks))
            )
            
            # Format results
            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                chunk = self.chunks[idx]
                # Convert distance to similarity score (1 - distance for cosine similarity)
                similarity_score = 1.0 - distance
                results.append({
                    'text': chunk.text,
                    'source_file': chunk.source_file,
                    'chunk_id': chunk.chunk_id,
                    'similarity_score': float(similarity_score),
                    'metadata': chunk.metadata
                })
            
            logger.debug(f"Found {len(results)} relevant passages for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error during vector search: {str(e)}")
            raise
    
    def _process_knowledge_base(self):
        """Process all files in the knowledge base"""
        knowledge_base_path = self.config.KNOWLEDGE_BASE_PATH
        
        if not os.path.exists(knowledge_base_path):
            raise FileNotFoundError(f"Knowledge base path not found: {knowledge_base_path}")
        
        self.chunks = []
        all_texts = []
        
        # Process each file in the knowledge base
        for filename in os.listdir(knowledge_base_path):
            if filename.endswith('.txt'):
                file_path = os.path.join(knowledge_base_path, filename)
                logger.info(f"Processing file: {filename}")
                
                try:
                    chunks = self._process_file(file_path, filename)
                    self.chunks.extend(chunks)
                    all_texts.extend([chunk.text for chunk in chunks])
                    
                except Exception as e:
                    logger.error(f"Error processing file {filename}: {str(e)}")
                    continue
        
        if not all_texts:
            raise ValueError("No text content found in knowledge base")
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(all_texts)} chunks...")
        self.embeddings = self.model.encode(all_texts, show_progress_bar=True)
        
        # Create scikit-learn NearestNeighbors index
        logger.info("Creating scikit-learn NearestNeighbors index...")
        
        # Normalize embeddings for cosine similarity
        self.embeddings_normalized = normalize(self.embeddings)
        
        # Use NearestNeighbors with cosine metric
        self.nearest_neighbors = NearestNeighbors(
            n_neighbors=min(10, len(self.embeddings_normalized)),  # Default to 10, will be overridden in search
            metric='cosine',
            algorithm='brute'  # Brute force for cosine similarity
        )
        self.nearest_neighbors.fit(self.embeddings_normalized)
        
        logger.info(f"Successfully processed {len(self.chunks)} chunks from {len([f for f in os.listdir(knowledge_base_path) if f.endswith('.txt')])} files")
    
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
        
        logger.debug(f"Created {len(chunks)} chunks from {source_file}")
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
                
                # Load embeddings and chunks
                with open(self.config.EMBEDDINGS_CACHE_PATH, 'rb') as f:
                    data = pickle.load(f)
                    self.chunks = data['chunks']
                    self.embeddings = data['embeddings']
                
                # Load scikit-learn index
                with open(self.config.INDEX_CACHE_PATH, 'rb') as f:
                    self.nearest_neighbors = pickle.load(f)
                
                return True
            
        except Exception as e:
            logger.warning(f"Failed to load cached data: {str(e)}")
        
        return False
    
    def _save_cached_data(self):
        """Save embeddings and index to cache"""
        try:
            # Save embeddings and chunks
            with open(self.config.EMBEDDINGS_CACHE_PATH, 'wb') as f:
                pickle.dump({
                    'chunks': self.chunks,
                    'embeddings': self.embeddings
                }, f)
            
            # Save scikit-learn index
            with open(self.config.INDEX_CACHE_PATH, 'wb') as f:
                pickle.dump(self.nearest_neighbors, f)
            
            logger.info("Cached embeddings and index saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save cached data: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector search engine"""
        if not self.is_ready():
            return {'status': 'not_ready'}
        
        return {
            'status': 'ready',
            'total_chunks': len(self.chunks),
            'vector_dimension': self.config.VECTOR_DIMENSION,
            'model_name': self.config.EMBEDDINGS_MODEL,
            'chunk_size': self.config.CHUNK_SIZE,
            'chunk_overlap': self.config.CHUNK_OVERLAP,
            'search_engine': 'scikit-learn NearestNeighbors'
        }
