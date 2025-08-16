# Environment Variables Template

Copy the following variables to your `.env` file in the backend directory and fill in your actual values:

```bash
# Smart RAG Backend Environment Variables Template
# Copy this file to .env and fill in your actual values

# Flask Server Configuration
HOST=127.0.0.1
PORT=5000
DEBUG=False

# API Control
API_CALLS_ENABLED=True

# DeepSeek API Configuration
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# Vector Search Configuration
EMBEDDINGS_MODEL=all-MiniLM-L6-v2
VECTOR_DIMENSION=384
CHUNK_SIZE=500
CHUNK_OVERLAP=50

# Cache Configuration (Redis)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
CACHE_TTL=3600

# Knowledge Base Paths
KNOWLEDGE_BASE_PATH=./knowledge_base
EMBEDDINGS_CACHE_PATH=./cache/embeddings.pkl
INDEX_CACHE_PATH=./cache/faiss_index.bin

# Response Generation Settings
MAX_CONTEXT_LENGTH=4000
MAX_RESPONSE_LENGTH=1000
TEMPERATURE=0.7
TOP_P=0.9

# Phone Authentication (Legacy)
APPROVED_PHONE_NUMBERS=

# JSONBin API Configuration
JSONBIN_API_KEY=your_jsonbin_api_key_here
JSONBIN_BASE_URL=https://api.jsonbin.io/v3
JSONBIN_BIN_ID=your_jsonbin_bin_id_here

# Stripe Payment Configuration
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
STRIPE_CURRENCY=usd
DONATION_SUCCESS_URL=http://127.0.0.1:3000/#/donation-success
DONATION_CANCEL_URL=http://127.0.0.1:3000/#/donation-cancel
```

## Stripe Setup Instructions

1. Create a Stripe account at https://stripe.com
2. Get your API keys from the Stripe Dashboard:
   - **Secret Key**: Found in "Developers" > "API keys" (starts with `sk_test_` for test mode)
   - **Publishable Key**: Found in "Developers" > "API keys" (starts with `pk_test_` for test mode)
3. Set up webhooks (optional but recommended):
   - Go to "Developers" > "Webhooks"
   - Add endpoint pointing to your backend URL + `/donate/webhook`
   - Select events: `checkout.session.completed`, `payment_intent.succeeded`
   - Copy the webhook secret (starts with `whsec_`)

## Security Notes

- Never commit your `.env` file to version control
- Use test keys during development
- Switch to live keys only in production
- Keep your webhook secret secure
