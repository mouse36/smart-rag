# JSONBin API Setup Guide

This guide explains how to set up user authentication using JSONBin.io for the Smart RAG application.

## Overview

The application now uses JSONBin.io as a simple cloud database to store user account information (usernames and hashed passwords). This allows for:

- User registration with username and password
- User login authentication
- Secure password storage (using SHA-256 hashing)
- Simple cloud-based user management

## Setup Instructions

### 1. Create a JSONBin Account

1. Go to [JSONBin.io](https://jsonbin.io/)
2. Sign up for a free account
3. Confirm your email address

### 2. Get Your API Key

1. After logging in, go to your dashboard
2. Navigate to "API Keys" section
3. Copy your Master API Key (starts with `$2b$10$` or similar)

### 3. Create a Bin for User Data

1. In your JSONBin dashboard, click "Create Bin"
2. Set the bin name to something like "smart-rag-users"
3. Initialize it with this content:
   ```json
   {
     "users": [],
     "last_updated": null,
     "version": 0
   }
   ```
4. Create the bin and copy the Bin ID (long alphanumeric string)

### 4. Configure Environment Variables

1. Copy `env.txt` to `.env` in your project root:
   ```bash
   cp env.txt .env
   ```

2. Edit `.env` and fill in your JSONBin credentials:
   ```bash
   # JSONBin API Settings (for user authentication)
   JSONBIN_API_KEY=your_actual_api_key_here
   JSONBIN_BASE_URL=https://api.jsonbin.io/v3
   JSONBIN_BIN_ID=your_actual_bin_id_here
   ```

### 5. Test the Integration

Run the test script to verify everything is working:

```bash
cd backend
python test_jsonbin.py
```

The script will:
- Test the connection to JSONBin
- Create a test user
- Test login functionality
- List users in the bin

## Security Considerations

### Password Security
- Passwords are hashed using SHA-256 before storage
- Original passwords are never stored in the bin
- Consider upgrading to bcrypt for production use

### API Security
- Keep your JSONBin API key secret
- Use environment variables, never commit keys to version control
- Consider using JSONBin's private bins for additional security

### Rate Limiting
- JSONBin has rate limits on their free tier
- The application handles rate limit errors gracefully
- Consider upgrading your JSONBin plan for higher limits

## User Management

### User Registration Flow
1. User enters username and password
2. Frontend validates input (minimum lengths, etc.)
3. Backend checks if username already exists
4. Password is hashed and user is added to the bin
5. Success response returned to frontend

### User Login Flow
1. User enters username and password
2. Frontend validates input
3. Backend searches for username in the bin
4. Password is hashed and compared with stored hash
5. Login success/failure response returned

### Error Handling
The system handles various error scenarios:
- Username already exists
- User not found
- Incorrect password
- API connection issues
- Rate limiting
- Service unavailable

## API Endpoints

The backend provides these authentication endpoints:

- `POST /auth/register` - Register new user
- `POST /auth/login` - Authenticate user login
- `GET /auth/users` - List all users (admin)
- `GET /auth/user/{username}` - Get user info (admin)
- `POST /auth/change-password` - Change user password
- `GET /auth/test` - Test JSONBin connection (admin)

## Frontend Integration

The frontend automatically switches between:
- **Phone authentication** (legacy system)
- **Username/password authentication** (new JSONBin system)

Users can toggle between authentication methods using the links on the login page.

## Troubleshooting

### Common Issues

1. **"JSONBin client not ready"**
   - Check that `JSONBIN_API_KEY` and `JSONBIN_BIN_ID` are set in `.env`
   - Verify the API key is correct

2. **"Invalid API key" error**
   - Double-check your API key from JSONBin dashboard
   - Make sure there are no extra spaces or characters

3. **"Bin not found" error**
   - Verify the bin ID is correct
   - Make sure the bin exists and is accessible

4. **Rate limit errors**
   - Wait for the rate limit to reset
   - Consider upgrading your JSONBin plan

### Debug Mode

To see detailed logs, set `DEBUG=True` in your `.env` file and restart the backend.

## Production Considerations

For production deployment, consider:

1. **Upgrading password hashing** to bcrypt or Argon2
2. **Using JSONBin's private bins** for additional security
3. **Implementing session management** with JWT tokens
4. **Adding email verification** for new accounts
5. **Implementing password reset** functionality
6. **Adding two-factor authentication** for enhanced security

## Migration from Phone Authentication

The system supports both phone and username/password authentication simultaneously. You can gradually migrate users or offer both options permanently.

To disable phone authentication:
1. Remove phone-related UI elements
2. Remove the `/auth/validate-phone` endpoint
3. Update the frontend to only show username/password forms
