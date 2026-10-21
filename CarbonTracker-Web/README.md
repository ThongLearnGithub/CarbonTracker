# Carbon Tracker Web

Standalone React + TypeScript web client for Carbon Tracker. This project is separate from the Flutter mobile app in `CarbonTracker-Flutter` and reads/writes the same FastAPI service and database.

## Requirements

- Node.js 22.12 or newer
- The Carbon Tracker FastAPI backend running
- The Firebase Web API key for the same Firebase project configured in the mobile app

## Local setup

From `Carbon Tracker Project`:

```powershell
cd carbon_backend
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload --host 0.0.0.0
```

In a second terminal:

```powershell
cd CarbonTracker-Web
Copy-Item .env.example .env.local
```

Edit `.env.local` and set `VITE_FIREBASE_API_KEY` to the Web API key for Firebase project `carbon-tracker-622b1`. Then run:

```powershell
npm install
npm run dev
```

Open the local URL printed by Vite. Sign in with the same verified Firebase email used in the mobile app. Home, trip history, credits, wallet, rewards, and account information are loaded from the shared backend. Trips logged from the web are written to the same API as mobile trips.

Email/password registration, sign-in, profile-name updates, email verification, and password reset use the Firebase JavaScript Auth SDK configured for the same Firebase project as `CarbonTracker-Flutter`. Newly registered accounts must verify their email before the backend creates or connects the Carbon Tracker user.

## Production deployment

Set `VITE_API_BASE_URL` to the public HTTPS API URL and `VITE_FIREBASE_API_KEY` before building:

```powershell
npm run build
npm run preview
```

Deploy the generated `dist` directory to a static web host. Also allow the hosted website origin in backend CORS and add the website domain to Firebase Authentication's authorized domains. Keep the backend and database private; never put database credentials or service-account private keys in Vite environment variables.

## Current backend constraints

The existing backend exposes some user-data routes by `user_id` and does not enforce the bearer token on every route. The web client matches that current contract for compatibility. Add backend authentication/authorization before making the API public. Voucher availability/status is currently controlled by the shared backend endpoint.
