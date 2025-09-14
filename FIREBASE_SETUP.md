# 🔥 Firebase Setup Guide for Store

## Step 1: Create Firebase Project

1. **Go to Firebase Console**: https://console.firebase.google.com/
2. **Click "Create a project"**
3. **Project name**: `solel-bone` (or any name you prefer)
4. **Google Analytics**: You can disable it for now (not needed)
5. **Click "Create project"**

## Step 2: Enable Firestore Database

1. **In Firebase Console**, click on **"Firestore Database"** in the left sidebar
2. **Click "Create database"**
3. **Security rules**: Choose **"Start in test mode"** (we'll secure it later)
4. **Location**: Choose closest to your users (e.g., `us-central1` for US, `europe-west1` for Europe)
5. **Click "Done"**

## Step 3: Create Service Account

1. **Go to Project Settings** (click gear icon in left sidebar)
2. **Click "Service accounts" tab**
3. **Click "Generate new private key"**
4. **Click "Generate key"** - This downloads a JSON file
5. **Save the JSON file** as `firebase-credentials.json` in your project root
6. **IMPORTANT**: Add `firebase-credentials.json` to your `.gitignore` (already done)

## Step 4: Configure Environment Variables

1. **Copy `.env.example` to `.env`**:
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file** and update Firebase settings:
   ```bash
   # Firebase Configuration
   FIREBASE_PROJECT_ID=your-project-id-here
   GOOGLE_APPLICATION_CREDENTIALS=firebase-credentials.json
   MOCK_FIREBASE=false
   
   # Other settings...
   SECRET_KEY=your-secret-key-change-this-in-production
   ```

3. **Find your Project ID**:
   - In Firebase Console, it's shown at the top of the page
   - Or in the JSON file you downloaded, look for `"project_id"`

## Step 5: Test Firebase Connection

Run this test to verify everything works:

```bash
python -c "
import firebase_admin
from firebase_admin import credentials, firestore

try:
    # Initialize Firebase
    cred = credentials.Certificate('firebase-credentials.json')
    firebase_admin.initialize_app(cred)
    
    # Test connection
    db = firestore.client()
    test_doc = db.collection('test').document('connection')
    test_doc.set({'timestamp': firestore.SERVER_TIMESTAMP, 'status': 'connected'})
    
    print('✅ Firebase connection successful!')
    
    # Clean up test document
    test_doc.delete()
    print('✅ Test document cleaned up')
    
except Exception as e:
    print(f'❌ Firebase connection failed: {e}')
"
```

## Step 6: Set Up Security Rules

1. **In Firebase Console**, go to **"Firestore Database"**
2. **Click "Rules" tab**
3. **Replace the default rules** with these secure rules:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can read/write their own data
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    // User sessions - only the user can access
    match /user_sessions/{sessionId} {
      allow read, write: if request.auth != null && 
        resource.data.user_id == request.auth.uid;
    }
    
    // Shopping lists - only owner can access
    match /shopping_lists/{listId} {
      allow read, write: if request.auth != null && 
        resource.data.user_id == request.auth.uid;
    }
    
    // User activities - only owner can read
    match /user_activities/{activityId} {
      allow read: if request.auth != null && 
        resource.data.user_id == request.auth.uid;
      allow write: if request.auth != null;
    }
  }
}
```

4. **Click "Publish"**

## Step 7: Optional - Enable Authentication (if needed later)

If you want to add email/password authentication later:

1. **Go to "Authentication"** in Firebase Console
2. **Click "Get started"**
3. **Click "Sign-in method" tab**
4. **Enable desired providers** (Email/Password recommended)

## Your Firebase Project Structure

Once set up, your Firestore will have these collections:

```
📁 your-firebase-project
├── 📂 users/
│   └── {user_id}/
│       ├── user_code: "ABC123"
│       ├── created_at: timestamp
│       ├── preferred_language: "hebrew"
│       └── last_activity: timestamp
│
├── 📂 user_sessions/
│   └── {session_id}/
│       ├── user_id: "user123"
│       ├── user_code: "ABC123"
│       ├── created_at: timestamp
│       └── last_activity: timestamp
│
├── 📂 shopping_lists/
│   └── {list_id}/
│       ├── user_id: "user123"
│       ├── list_name: "My Project"
│       ├── items: [array of products]
│       ├── created_at: timestamp
│       └── updated_at: timestamp
│
└── 📂 user_activities/
    └── {activity_id}/
        ├── user_id: "user123"
        ├── type: "search"
        ├── description: "Searched for cables"
        └── timestamp: timestamp
```

## Troubleshooting

### Error: "Permission denied"
- Check your security rules
- Ensure `MOCK_FIREBASE=false` in `.env`
- Verify the service account JSON file path

### Error: "Project not found"
- Double-check the `FIREBASE_PROJECT_ID` in `.env`
- Make sure it matches exactly what's in Firebase Console

### Error: "Invalid credentials"
- Verify the `firebase-credentials.json` file is in the right location
- Check the `GOOGLE_APPLICATION_CREDENTIALS` path in `.env`

### Error: "Firebase already initialized"
- This is normal if restarting the app - Firebase handles this automatically

## Next Steps

Once Firebase is set up:

1. **Set `MOCK_FIREBASE=false`** in your `.env` file
2. **Restart your Flask application**
3. **Test user registration** by entering a code
4. **Check Firebase Console** to see data being stored

Your Store will now have persistent data storage with real user accounts and shopping lists! 🎉