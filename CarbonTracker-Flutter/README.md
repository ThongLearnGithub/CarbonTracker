# Carbon Tracker

Flutter application for tracking trips, carbon savings, credits, wallet activity, and vouchers. The same app runs on Android/iOS and in a desktop or mobile browser.

## Run the web app locally

From the `Carbon Tracker Project` directory, start the FastAPI backend in one terminal:

```powershell
cd carbon_backend
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload --host 0.0.0.0
```

In another terminal, from the same `Carbon Tracker Project` directory, run the Flutter app in Chrome:

```powershell
cd "CarbonTracker - Flutter"
flutter pub get
flutter run -d chrome --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

The web app authenticates with the configured Firebase project and loads trip, wallet, voucher, and homepage data from the same FastAPI API/database as the mobile app. Signing into the same account therefore shows the same server-side data.

For an Android emulator, the app's default API URL is `http://10.0.2.2:8000`. For a physical phone on the same Wi-Fi as the backend, pass the computer's LAN IP as `API_BASE_URL` (for example, `http://192.168.1.20:8000`) when running the mobile app. For a deployed mobile app and website, build both with the same public HTTPS API URL.

## Build for hosting

Build the static web app with the URL of the deployed backend:

```powershell
flutter build web --release --dart-define=API_BASE_URL=https://your-api.example.com
```

Publish the contents of `build/web` to a static web host. For production:

- Serve the website and API over HTTPS.
- Configure the API's CORS allow-list to include the website origin.
- Add the website domain to Firebase Authentication's authorized domains.
- Set `API_BASE_URL` to the reachable API base URL when building. The default `127.0.0.1` is only for local development.

The GPS map/tracking screen also needs the browser's location permission and a valid Google Maps JavaScript API key configured for the web deployment.
