# 🎓 Aaj Ka Freelancer

### College students earning through skills.

A full-stack Flask web application that connects college students. **Google Sign-In** + **Firebase Firestore** for auth and realtime chat.

---

## ✨ Features

### 🔐 Authentication (Google Sign-In)
- **Step 1:** Sign in with Google (Gmail or any Google account)
- **Step 2:** Complete profile form (if new user) – college, branch, skills, etc.
- No email verification, no passwords to remember

### 👤 Profile & Community
- Edit profile, upload photo
- Worker toggle and skill tags
- Discover people and workers by skill

### 💬 Realtime Chat
- Firebase Firestore for messages
- Realtime updates, unread counts
- Hire request flow within chat

---

## 🛠 Tech Stack

| Layer   | Technology                            |
|---------|---------------------------------------|
| Backend | Python, Flask, Flask-SQLAlchemy, Flask-Login |
| Auth    | Firebase Authentication (Google)      |
| Database| SQLite / PostgreSQL (Flask), Firestore (chat) |
| Frontend| HTML5, CSS3, Vanilla JS, Bootstrap 5  |

---

## 📦 Installation

### 1. Clone and setup

```bash
git clone <repo-url>
cd aajkafreelancer
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
```

### 2. Firebase project setup (do this externally)

#### A. Create Firebase project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click **Add project** → choose a name → create

#### B. Enable Google Sign-In

1. In Firebase Console → **Authentication** → **Sign-in method**
2. Enable **Google**
3. Add your support email (e.g. your Gmail)
4. Save

#### C. Create Firestore database

1. Go to **Firestore Database** → **Create database**
2. Choose **Start in production mode** (we’ll add rules next)
3. Pick a region

#### D. Firestore security rules

1. Go to **Firestore Database** → **Rules**
2. Replace with:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{userId} {
      allow read: if request.auth != null;
      allow write: if request.auth != null;
    }
    match /conversations/{convId} {
      allow read, write: if request.auth != null;
      match /messages/{msgId} {
        allow read, write: if request.auth != null;
      }
    }
    match /conversation_members/{docId} {
      allow read, write: if request.auth != null;
    }
  }
}
```

#### E. Get Web config and service account

1. **Web config (for frontend):**
   - Project settings (gear) → **General** → **Your apps**
   - Add web app if needed
   - Copy `apiKey`, `authDomain`, `projectId`, `storageBucket`, `messagingSenderId`, `appId`

2. **Service account (for backend):**
   - Project settings → **Service accounts**
   - **Generate new private key** → save JSON file
   - Put it in project root as `firebase-service-account.json` (or another path you prefer)

#### F. Firestore indexes (if Firestore asks for them)

When you use chat, Firestore may prompt you to create indexes. Click the link in the error message to auto-create them, or add manually:

- Collection: `conversations/{convId}/messages`  
  Fields: `created_at` (Descending)

---

### 3. Environment variables

Create `.env` in project root:

```env
# Flask
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///college_earning.db

# Firebase (frontend - from Web app config)
FIREBASE_API_KEY=AIza...
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
FIREBASE_MESSAGING_SENDER_ID=123456789
FIREBASE_APP_ID=1:123456789:web:abc123

# Firebase (backend - path to service account JSON)
FIREBASE_CREDENTIALS_PATH=firebase-service-account.json
```

**Important:** Add `firebase-service-account.json` and `.env` to `.gitignore`. Never commit them.

---

### 4. Database migration

```bash
flask db upgrade
```

For SQLite (new project), tables are created automatically on first run.

---

## 🗄️ Database setup (PostgreSQL / Production)

Because Vercel is serverless, you should apply DB schema changes **outside** the running app (one-time).

### Option A (Recommended): Run the provided setup script

This repo includes `scripts/db_setup.py` which:
- creates missing tables (`db.create_all()`)
- applies hybrid-auth fixes (password_hash nullable, firebase_uid column/index)

Run it **from your machine** pointing to the production database:

Windows (PowerShell):

```powershell
cd d:\Cipher\aajkafreelancer
$env:DATABASE_URL="postgresql://USER:PASS@HOST:5432/DB"
$env:SECRET_KEY="any-non-empty-value"
$env:FIREBASE_PROJECT_ID="aaj-ka-freelancer"
.\venv\Scripts\python scripts\db_setup.py
```

Linux/Mac:

```bash
export DATABASE_URL="postgresql://USER:PASS@HOST:5432/DB"
export SECRET_KEY="any-non-empty-value"
export FIREBASE_PROJECT_ID="aaj-ka-freelancer"
python scripts/db_setup.py
```

### Option B: Manual SQL (quick fix for the current error)

Run this directly on your Postgres DB:

```sql
ALTER TABLE "user"
ALTER COLUMN password_hash DROP NOT NULL;

ALTER TABLE "user"
ADD COLUMN IF NOT EXISTS firebase_uid VARCHAR(128);

CREATE UNIQUE INDEX IF NOT EXISTS uq_user_firebase_uid ON "user"(firebase_uid);
```

If you already have a `firebase_uid` unique constraint/index, you can skip the last statement.

---

### 5. Run the app

```bash
python run.py
# Or: flask run
```

Open http://127.0.0.1:5000

---

## 📂 Project structure

```
aajkafreelancer/
├── app/
│   ├── auth/          # Google Sign-In, complete profile, logout
│   ├── main/          # Dashboard, people, profile, edit
│   ├── chat/          # Chat routes, Firestore integration
│   ├── firebase_client.py   # Firebase Admin, Firestore helpers
│   ├── models.py      # User, HireRequest
│   └── ...
├── templates/
├── static/
│   └── js/
│       ├── chat.js    # Firestore realtime chat
│       └── forms.js
├── config.py
├── requirements.txt
├── .env               # Create this (not in git)
└── firebase-service-account.json  # Create this (not in git)
```

---

## 🔒 Security

- `.env` and `firebase-service-account.json` must not be committed
- Firebase rules restrict Firestore access to authenticated users
- Use HTTPS in production
- For production DB, use PostgreSQL (e.g. Vercel Postgres, Supabase DB only, etc.)

---

## 🚀 Deployment (Vercel)

### Prerequisites
- Firebase project created, Google Auth and Firestore enabled
- PostgreSQL database (e.g. Supabase, Vercel Postgres, Neon)
- Vercel account

### Step 1: Environment variables (Vercel Dashboard)

Add these in **Vercel Project → Settings → Environment Variables**:

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Random string for Flask sessions (e.g. `openssl rand -hex 32`) |
| `DATABASE_URL` | PostgreSQL connection string |
| `FIREBASE_API_KEY` | From Firebase Web app config |
| `FIREBASE_AUTH_DOMAIN` | e.g. `your-project.firebaseapp.com` |
| `FIREBASE_PROJECT_ID` | Your Firebase project ID |
| `FIREBASE_STORAGE_BUCKET` | e.g. `your-project.firebasestorage.app` |
| `FIREBASE_MESSAGING_SENDER_ID` | From Firebase config |
| `FIREBASE_APP_ID` | From Firebase config |
| `FIREBASE_CREDENTIALS_JSON` | **Full JSON content** of service account file (paste entire JSON) |
| `MAIL_SERVER` | `smtp.gmail.com` |
| `MAIL_PORT` | `587` |
| `MAIL_USE_TLS` | `True` |
| `MAIL_USERNAME` | Your Gmail |
| `MAIL_PASSWORD` | Gmail App Password |
| `MAIL_DEFAULT_SENDER` | Same as MAIL_USERNAME |

**FIREBASE_CREDENTIALS_JSON:** Copy the entire content of `firebase-service-account.json` and paste as the value. No file upload needed.

### Step 2: Firebase authorized domains

1. Firebase Console → **Authentication** → **Settings** → **Authorized domains**
2. Add your Vercel domain (e.g. `your-app.vercel.app`)

### Step 3: Deploy

```bash
# Install Vercel CLI (optional)
npm i -g vercel

# Deploy
vercel
# Or connect GitHub repo in Vercel dashboard and auto-deploy on push
```

### Step 4: Post-deploy checks

- [ ] Google Sign-In works
- [ ] Complete profile form works for new users
- [ ] Chat loads and sends messages
- [ ] Profile image upload works (stored in /tmp on Vercel – ephemeral; consider Firebase Storage for persistence)

### Notes

- **Profile images on Vercel:** Uploaded images are stored in `/tmp` and are ephemeral. For persistent storage, integrate Firebase Storage.
- **Database:** Run migrations before first deploy: `flask db upgrade` (or ensure schema is applied).
- **No files to manually upload** – all config goes in Vercel env vars.

---

## 📝 Auth flow

1. User visits **Sign In** → clicks **Continue with Google**
2. Google popup → user signs in
3. Backend verifies Firebase token, checks if user exists
4. **Existing user:** redirect to dashboard
5. **New user:** redirect to **Complete profile** form
6. User fills college, branch, skills, etc. → account created → redirect to dashboard

---

## Support

For issues, open a GitHub issue or contact the team.
