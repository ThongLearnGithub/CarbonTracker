# Carbon Tracker Flutter App

Flutter mobile app for tracking trips, carbon savings, credits, wallet activity, and vouchers. The separate React website is in `CarbonTracker-Web`.

## Run on Android

From the repository root:

```powershell
cd CarbonTracker-Flutter
flutter pub get
flutter devices
flutter run -d <android-device-id>
```

Start an Android emulator in Android Studio's Device Manager or connect a phone with USB debugging enabled if no Android device is listed. Do not select a browser device when you want the native mobile app.

The Android emulator can reach a backend running on the host computer at `http://10.0.2.2:8000`. A physical phone needs the computer's LAN IP, for example `http://192.168.1.20:8000`.

## Run the Flutter app in a browser

This runs the Flutter app as a browser app; it does not run the separate React website:

```powershell
cd CarbonTracker-Flutter
flutter pub get
flutter run -d edge
```

## Run the React website

Use the separate `CarbonTracker-Web` folder and its Vite commands. See [the web app README](../CarbonTracker-Web/README.md).

## Build Android

```powershell
cd CarbonTracker-Flutter
flutter build apk --release
```
