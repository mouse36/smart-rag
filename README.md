# Smart RAG - Selective Mutism Virtual Assistant

A virtual assistant chatbot powered by the DeepSeek API that provides expert guidance on selective mutism through retrieval-augmented generation (RAG). The system uses semantic search to find relevant information from a comprehensive knowledge base and generates informed responses using the DeepSeek API.

## Features

- 🤖 **AI-Powered Responses**: Uses DeepSeek API for intelligent, context-aware responses
- 📚 **Knowledge Base**: Comprehensive information about selective mutism from expert sources
- 🔍 **Vector Search**: Semantic similarity search to find the most relevant information
- ⚡ **Caching**: Redis-based caching for improved response times
- 🎨 **Beautiful UI**: Modern, responsive chat interface
- 🔧 **Health Monitoring**: Built-in health checks and error handling

## Architecture

```
Frontend (HTML/JS) → Backend (Flask) → [DeepSeek API + Vector Search + Cache]
                                           ↓
                                    Knowledge Base (Text Files)
```

## Quick Start

### Prerequisites

1. **Python 3.8+**
2. **DeepSeek API Key** - Get one from [DeepSeek](https://platform.deepseek.com/)
3. **Redis** (optional, for caching - falls back to memory cache if not available)

### Installation

1. **Clone or navigate to the project directory**
   ```bash
   cd smart-rag
   ```

2. **Install Python dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   export DEEPSEEK_API_KEY="your_deepseek_api_key_here"
   ```

4. **Start the backend server**
   ```bash
   python run.py
   ```

5. **Open the frontend**
   - Open `frontend/index.html` in your web browser
   - Or serve it with a simple HTTP server:
     ```bash
     cd frontend
     python -m http.server 8000
     ```
   - Then visit `http://localhost:8000`

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | *(required)* | Your DeepSeek API key |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | DeepSeek API base URL |
| `DEEPSEEK_MODEL` | `deepseek-chat` | Model to use |
| `HOST` | `127.0.0.1` | Server host |
| `PORT` | `5000` | Server port |
| `DEBUG` | `True` | Debug mode |
| `EMBEDDINGS_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model |
| `CHUNK_SIZE` | `500` | Text chunk size for processing |
| `REDIS_HOST` | `localhost` | Redis host (optional) |
| `REDIS_PORT` | `6379` | Redis port (optional) |

### Advanced Configuration

You can customize the system by modifying values in `backend/config.py` or setting environment variables.

## Knowledge Base

The system comes with a comprehensive knowledge base about selective mutism located in `backend/knowledge_base/`. The knowledge base includes:

- Clinical research and findings
- Treatment approaches and interventions
- Parent and teacher guidance
- Educational strategies
- Medication information
- Case studies and practical examples

### Adding New Knowledge

To add new knowledge to the system:

1. Add `.txt` files to the `backend/knowledge_base/` directory
2. Restart the backend server (it will automatically process new files)
3. The system will generate embeddings and update the search index

## API Endpoints

### Main Endpoints

- **POST** `/chat` - Main chat endpoint
  ```json
  {
    "message": "How can I help a child with selective mutism?"
  }
  ```

- **GET** `/health` - Health check endpoint
- **POST** `/search` - Direct knowledge base search
- **GET** `/cache/stats` - Cache statistics
- **POST** `/cache/clear` - Clear cache

### Example Chat Request

```bash
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the main characteristics of selective mutism?"}'
```

## How It Works

1. **User Input**: User types a question in the chat interface
2. **Vector Search**: The system searches the knowledge base using semantic similarity
3. **Context Retrieval**: Top 5-7 most relevant passages are retrieved
4. **AI Generation**: DeepSeek API generates a response using the retrieved context
5. **Caching**: Response is cached for faster future retrieval
6. **Display**: Response is displayed to the user

## Performance Optimization

- **Embeddings Caching**: Vector embeddings are cached to disk after first generation
- **Response Caching**: Common queries are cached using Redis
- **Efficient Search**: FAISS vector index for fast similarity search
- **Chunking Strategy**: Text is intelligently chunked with overlap for better context

## Troubleshooting

### Backend Won't Start

1. **Check API Key**: Ensure `DEEPSEEK_API_KEY` is set correctly
2. **Check Dependencies**: Run `pip install -r requirements.txt`
3. **Check Knowledge Base**: Ensure `.txt` files exist in `backend/knowledge_base/`

### Frontend Shows Connection Error

1. **Backend Running**: Ensure backend is running on `http://localhost:5000`
2. **CORS Issues**: The backend includes CORS headers for local development
3. **Network**: Check firewall and network connectivity

### Slow Responses

1. **First Run**: Initial setup generates embeddings (this is slow but only happens once)
2. **Cache**: Enable Redis for better caching performance
3. **Hardware**: Consider using GPU support for faster embeddings

### Memory Issues

1. **Large Knowledge Base**: Consider reducing chunk size or using GPU acceleration
2. **Cache Size**: Monitor Redis memory usage or in-memory cache size

## Development

### Project Structure

```
smart-rag/
├── backend/
│   ├── app.py              # Main Flask application
│   ├── vector_search.py    # Vector search engine
│   ├── deepseek_client.py  # DeepSeek API client
│   ├── cache_manager.py    # Cache management
│   ├── config.py          # Configuration
│   ├── run.py             # Startup script
│   ├── requirements.txt   # Python dependencies
│   ├── knowledge_base/    # Knowledge base files
│   └── cache/            # Generated embeddings and indices
└── frontend/
    └── index.html        # Chat interface
```

### Adding Features

1. **New Endpoints**: Add routes in `app.py`
2. **Enhanced Search**: Modify `vector_search.py`
3. **UI Changes**: Update `frontend/index.html`

## Security Considerations

- **API Keys**: Never commit API keys to version control
- **Input Validation**: The system includes basic input validation
- **Rate Limiting**: Consider adding rate limiting for production use
- **HTTPS**: Use HTTPS in production environments

## License

This project is for educational and research purposes. Please ensure compliance with DeepSeek's terms of service and any applicable data usage restrictions.

## Support

For technical issues:
1. Check the logs in the backend console
2. Verify all prerequisites are installed
3. Ensure network connectivity to DeepSeek API
4. Check the `/health` endpoint for component status

For questions about selective mutism, consult with qualified professionals specializing in this area.
