"""
Semantic Chunker for StructRAG MCP
Splits text into semantic chunks with overlap
"""
from typing import List, Dict
import logging
import tiktoken

logger = logging.getLogger(__name__)


class SemanticChunker:
    """
    Chunk text into semantic units with token-based boundaries
    Default: 512 tokens per chunk, 50 token overlap
    """
    
    def __init__(self, chunk_size: int = 512, overlap: int = 50, model: str = "gpt-4"):
        """
        Initialize chunker
        
        Args:
            chunk_size: Target tokens per chunk
            overlap: Overlapping tokens between chunks
            model: Model name for tokenizer
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback to cl100k_base (used by gpt-4, gpt-3.5-turbo)
            self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def chunk(self, text: str, metadata: Dict = None) -> List[Dict[str, any]]:
        """
        Split text into chunks
        
        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to each chunk
            
        Returns:
            List of chunks with metadata
        """
        if not text or not text.strip():
            return []
        
        # Tokenize
        tokens = self.encoding.encode(text)
        total_tokens = len(tokens)
        
        chunks = []
        start_idx = 0
        chunk_idx = 0
        
        while start_idx < total_tokens:
            # Get chunk tokens
            end_idx = min(start_idx + self.chunk_size, total_tokens)
            chunk_tokens = tokens[start_idx:end_idx]
            
            # Decode back to text
            chunk_text = self.encoding.decode(chunk_tokens)
            
            # Create chunk metadata
            chunk_meta = {
                "start_token": start_idx,
                "end_token": end_idx,
                "char_count": len(chunk_text)
            }
            
            # Add document metadata if provided
            if metadata:
                chunk_meta.update(metadata)
            
            chunks.append({
                "text": chunk_text,
                "chunk_index": chunk_idx,
                "token_count": len(chunk_tokens),
                "metadata": chunk_meta
            })
            
            # Move to next chunk with overlap
            start_idx += self.chunk_size - self.overlap
            chunk_idx += 1
        
        logger.info(f"Created {len(chunks)} chunks from {total_tokens} tokens")
        return chunks
    
    def chunk_by_sentences(self, text: str, metadata: Dict = None) -> List[Dict[str, any]]:
        """
        Alternative: Chunk by sentences (respecting semantic boundaries)
        Falls back to token-based if sentences are too long
        """
        # Simple sentence splitting
        sentences = self._split_sentences(text)
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        chunk_idx = 0
        
        for sentence in sentences:
            sentence_tokens = len(self.encoding.encode(sentence))
            
            # If single sentence exceeds chunk size, split it
            if sentence_tokens > self.chunk_size:
                if current_chunk:
                    # Save current chunk
                    chunks.append(self._create_chunk(
                        " ".join(current_chunk), 
                        chunk_idx, 
                        metadata
                    ))
                    chunk_idx += 1
                    current_chunk = []
                    current_tokens = 0
                
                # Split long sentence by tokens
                sentence_chunks = self.chunk(sentence, metadata)
                chunks.extend(sentence_chunks)
                continue
            
            # Add sentence to current chunk
            if current_tokens + sentence_tokens <= self.chunk_size:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
            else:
                # Save current chunk and start new one
                chunks.append(self._create_chunk(
                    " ".join(current_chunk), 
                    chunk_idx, 
                    metadata
                ))
                chunk_idx += 1
                
                # Start new chunk with overlap
                overlap_sentences = current_chunk[-2:] if len(current_chunk) >= 2 else current_chunk
                current_chunk = overlap_sentences + [sentence]
                current_tokens = sum(len(self.encoding.encode(s)) for s in current_chunk)
        
        # Add final chunk
        if current_chunk:
            chunks.append(self._create_chunk(
                " ".join(current_chunk), 
                chunk_idx, 
                metadata
            ))
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """Simple sentence splitter"""
        # Basic sentence splitting (can be enhanced with nltk/spacy)
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _create_chunk(self, text: str, chunk_idx: int, metadata: Dict = None) -> Dict[str, any]:
        """Create chunk dictionary"""
        tokens = self.encoding.encode(text)
        chunk_meta = {
            "chunk_index": chunk_idx,
            "token_count": len(tokens),
            "char_count": len(text)
        }
        
        if metadata:
            chunk_meta.update(metadata)
        
        return {
            "text": text,
            "metadata": chunk_meta
        }
