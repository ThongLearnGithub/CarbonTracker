# Carbon Tracker

Carbon Tracker is a multi-platform carbon-footprint tracker. The repository keeps the mobile app, API backend, and standalone React web app together while keeping each application in its own folder.

## Repository structure

```text
CarbonTracker/
├── CarbonTracker-Flutter/   # Android/iOS app and Flutter Web client
├── carbon_backend/          # FastAPI REST API and database integration
│   └── routing/             # low-carbon routing engine (API under /routing, see 

## Shared account and data

Both clients use the FastAPI backend in `carbon_backend`. To see the same trips, credits, wallet activity, and vouchers, run both clients against the same backend and database. Sign in with the same verified Firebase account.

## Start the backend

Copy `carbon_backend/.env.example` to `carbon_backend/.env` and set your local database URL and Firebase project. `.env` is intentionally excluded from Git. Install backend requirements in a local virtual environment, apply the database migrations, then run:

```powershell
cd carbon_backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head              # create or update the database schema
python -m scripts.seed            # optional: demo users, vouchers and trips (password "123")
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Run the backend tests with `pytest` (they use an in-memory SQLite database). After pulling a change that adds a file under `carbon_backend/alembic/versions/`, run `alembic upgrade head` again.

All user-specific endpoints (`/homepage`, `/trips`, `/wallet`, voucher redemption) identify the user from the `Authorization: Bearer <access_token>` header returned by `/auth/firebase` or `/auth/login`. Tokens expire after 7 days (`ACCESS_TOKEN_TTL_DAYS`).

The routing engine loads its road graph at start-up (about 2 seconds). Its test map is at `http://127.0.0.1:8000/routing/map`.

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

Configure production CORS to allow only the deployed web origin (`CORS_ORIGINS`, and set `CORS_ORIGIN_REGEX=` to drop the localhost default), use HTTPS, and keep database credentials, `.env` files, and service-account private keys out of Git.
