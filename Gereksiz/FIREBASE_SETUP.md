# Firebase Setup Instructions

## 1. Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Add project"
3. Enter project name: `uniride` (or your preferred name)
4. Follow the setup wizard

## 2. Enable Authentication

1. In Firebase Console, go to "Authentication"
2. Click "Get started"
3. Enable "Email/Password" sign-in method
4. Optionally, enable other methods if needed

## 3. Create Firestore Database

1. In Firebase Console, go to "Firestore Database"
2. Click "Create database"
3. Start in **production mode** (you can change rules later)
4. Choose a location (preferably close to your users)

## 4. Set Firestore Security Rules

Go to Firestore Database > Rules and add:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users collection
    match /users/{userId} {
      allow read: if request.auth != null;
      allow write: if request.auth != null && request.auth.uid == userId;
      allow create: if request.auth != null;
      // Admins can read/write all users
      allow read, write: if request.auth != null && 
        get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role == 'admin';
    }
    
    // Weekly schedules
    match /weeklySchedules/{scheduleId} {
      allow read: if request.auth != null;
      allow write: if request.auth != null;
    }
    
    // Ride requests
    match /rideRequests/{requestId} {
      allow read: if request.auth != null;
      allow create: if request.auth != null;
      allow update: if request.auth != null;
      // Admins can update all requests
      allow update: if request.auth != null && 
        get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role == 'admin';
    }
    
    // Vehicles (admin only)
    match /vehicles/{vehicleId} {
      allow read: if request.auth != null;
      allow write: if request.auth != null && 
        get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role == 'admin';
    }
    
    // Routes
    match /routes/{routeId} {
      allow read: if request.auth != null;
      allow write: if request.auth != null && 
        get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role == 'admin';
    }
    
    // Route assignments
    match /routeAssignments/{assignmentId} {
      allow read: if request.auth != null;
      allow write: if request.auth != null && 
        get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role == 'admin';
    }
    
    // Notifications
    match /notifications/{notificationId} {
      allow read: if request.auth != null && 
        resource.data.userId == request.auth.uid;
      allow create: if request.auth != null;
    }
    
    // Admin settings (admin only)
    match /adminSettings/{settingsId} {
      allow read: if request.auth != null;
      allow write: if request.auth != null && 
        get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role == 'admin';
    }
  }
}
```

## 5. Get Firebase Configuration

1. In Firebase Console, go to Project Settings (gear icon)
2. Scroll down to "Your apps"
3. Click the web icon (`</>`)
4. Register your app (nickname: "UniRide Web")
5. Copy the Firebase configuration object

## 6. Create .env.local File

Create `.env.local` in the project root:

```env
# Firebase Configuration
NEXT_PUBLIC_FIREBASE_API_KEY=your_api_key_here
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your_project_id.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your_project_id
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your_project_id.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=your_messaging_sender_id
NEXT_PUBLIC_FIREBASE_APP_ID=your_app_id

# Firebase Emulators (for local development - optional)
NEXT_PUBLIC_USE_FIREBASE_EMULATORS=false

# Google AI API Key (for Genkit)
GOOGLE_GENAI_API_KEY=your_google_ai_api_key_here
```

Replace the placeholder values with your actual Firebase configuration.

## 7. Create Initial Admin User

After setting up Firebase, you'll need to create an admin user:

1. Use Firebase Console > Authentication > Add user
2. Or use the registration form in the app, then update the user's role to "admin" in Firestore

To set a user as admin:
1. Go to Firestore Database
2. Open the `users` collection
3. Find the user document
4. Edit the document and set `role: "admin"`

## 8. Firebase Free Tier Limits

The Firebase free (Spark) plan includes:
- **Authentication**: 50K monthly active users
- **Firestore**: 
  - 1 GB storage
  - 20K reads/day
  - 20K writes/day
  - 20K deletes/day

For ~30-40 students, this should be sufficient for MVP.

## 9. Testing Locally

You can use Firebase Emulators for local development:

1. Install Firebase CLI: `npm install -g firebase-tools`
2. Initialize emulators: `firebase init emulators`
3. Set `NEXT_PUBLIC_USE_FIREBASE_EMULATORS=true` in `.env.local`
4. Start emulators: `firebase emulators:start`

## Notes

- The `.env.local` file is already in `.gitignore` - never commit your Firebase keys!
- Always use environment variables for sensitive configuration
- Test security rules thoroughly before production deployment

