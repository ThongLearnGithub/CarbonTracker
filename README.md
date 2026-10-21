# Carbon Tracker

Carbon Tracker is a multi-platform carbon-footprint tracker. The repository keeps the mobile app, API backend, and standalone React web app together while keeping each application in its own folder.

## Repository structure

```text
CarbonTracker/
├── CarbonTracker-Flutter/   # Android/iOS app and Flutter Web client
├── carbon_backend/          # FastAPI REST API and database integration
└── CarbonTracker-Web/       # Standalone React + TypeScript web client
```

## Shared account and data

Both clients use the FastAPI backend in `carbon_backend`. To see the same trips, credits, wallet activity, and vouchers, run both clients against the same backend and database. Sign in with the same verified Firebase account.

## Start the backend

Create and configure `carbon_backend/.env` for your local database and Firebase project. This file is intentionally excluded from Git. Install backend requirements in a local virtual environment, then run:

```powershell
cd carbon_backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## Run the standalone React web app

Run this app from `CarbonTracker-Web`; it is separate from the Flutter app:

```powershell
cd CarbonTracker-Web
Copy-Item .env.example .env.local
```

Set `VITE_FIREBASE_API_KEY` in `.env.local` to the Firebase Web API key for the same Firebase project, then run:

```powershell
npm install
npm run dev
```

Vite prints the local URL, normally `http://localhost:5173`. This opens the React web interface.

## Run the Flutter mobile app

Run this app from `CarbonTracker-Flutter`, and choose an Android device or emulator:

```powershell
cd CarbonTracker-Flutter
flutter pub get
flutter devices
flutter run -d <android-device-id>
```

If no Android device appears, start an emulator in Android Studio's Device Manager or connect an Android phone with USB debugging enabled, then run `flutter devices` again. Do not select Edge or Chrome if you want the native mobile app.

Running `flutter run -d edge` (or `-d chrome`) launches the Flutter app in a browser; it is not the standalone React app. To run the React web app, use the `CarbonTracker-Web` steps above.

For a phone connected over Wi-Fi, configure the API URL to use the computer's LAN IP. A phone cannot reach the computer through `127.0.0.1`.

## Security before deployment

The backend currently has routes that accept a `user_id` without enforcing the bearer token on every endpoint. Add and verify backend authorization before making the API public. Configure production CORS to allow only the deployed web origin, use HTTPS, and keep database credentials, `.env` files, and service-account private keys out of Git.
