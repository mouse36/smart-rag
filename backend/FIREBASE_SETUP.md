# Firebase Setup Guide

This guide explains how to set up Firebase Firestore to replace JSONBin for user authentication and data storage.

## Prerequisites

1. A Google Cloud Platform account
2. Firebase project created
3. Python environment with firebase-admin package installed

## Step 1: Create a Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Create a project" or select an existing project
3. Follow the setup wizard to create your project
4. Note down your Project ID (e.g., "sunnymentor")

## Step 2: Enable Firestore Database

1. In your Firebase project console, go to "Firestore Database"
2. Click "Create database"
3. Choose "Start in test mode" for development (you can secure it later)
4. Select a location for your database (choose the closest to your users)

## Step 3: Create a Service Account

1. In your Firebase project console, go to "Project settings" (gear icon)
2. Go to the "Service accounts" tab
3. Click "Generate new private key"
4. Download the JSON file - this is your service account key
5. **Important**: Keep this file secure and never commit it to version control

## Step 4: Configure Environment Variables

Set the following environment variables:

```bash
# Required
FIREBASE_PROJECT_ID=your-project-id

# Optional (if using service account key file)
FIREBASE_SERVICE_ACCOUNT_KEY=path/to/your/service-account-key.json
```

### Alternative: Using Application Default Credentials

If you're running on Google Cloud Platform or have set up Application Default Credentials, you can omit the `FIREBASE_SERVICE_ACCOUNT_KEY` variable.

## Step 5: Update Configuration

The application will automatically use Firebase when the `FIREBASE_PROJECT_ID` environment variable is set. The old JSONBin configuration is kept for backward compatibility but is no longer required.

## Step 6: Test the Setup

1. Start your application
2. Check the `/health` endpoint to verify Firebase client is ready
3. Try registering a new user to test the connection

## Data Structure

Firebase Firestore will automatically create the following structure:

```
accounts (collection)
├── user1_doc_id (document)
│   ├── email: "user@example.com"
│   ├── username: "user"
│   ├── password-hash: "hashed_password"
│   ├── status: "pending"
│   ├── admin: false
│   ├── online: true
│   ├── last-seen: "2024-01-01T00:00:00"
│   ├── chat-history: []
│   └── created_at: "2024-01-01T00:00:00"
└── user2_doc_id (document)
    └── ...
```

## Security Rules (Optional)

For production, you should set up Firestore security rules. Here's a basic example:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /accounts/{userId} {
      allow read, write: if request.auth != null;
    }
  }
}
```

## Migration from JSONBin

If you have existing data in JSONBin, you can migrate it by:

1. Export your data from JSONBin
2. Use the Firebase Admin SDK to import the data
3. Update user passwords (they will need to be re-hashed)

## Troubleshooting

### Common Issues

1. **Authentication Error**: Check your service account key file path and permissions
2. **Project Not Found**: Verify your `FIREBASE_PROJECT_ID` is correct
3. **Permission Denied**: Ensure your service account has the necessary permissions

### Debug Mode

Enable debug logging by setting the log level:

```python
import logging
logging.getLogger('firebase_admin').setLevel(logging.DEBUG)
```

## Support

For Firebase-specific issues, refer to:
- [Firebase Documentation](https://firebase.google.com/docs)
- [Firebase Admin SDK Python](https://firebase.google.com/docs/admin/setup)
- [Firestore Documentation](https://firebase.google.com/docs/firestore)
