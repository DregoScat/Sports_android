# AI Fitness Monitor - Android App

This Android application connects to the Python Flask backend server to display real-time fitness analysis (Squat and Jump modes).

## Prerequisites

1. **Android Studio** (Arctic Fox or later)
2. **Python server running** (`app.py`)
3. Both devices on the **same WiFi network**

## Setup Instructions

### 1. Open in Android Studio

1. Open Android Studio
2. Select "Open an existing project"
3. Navigate to `android_app` folder and select it
4. Wait for Gradle sync to complete

### 2. Find Your Computer's IP Address

**Windows:**
```powershell
ipconfig
```
Look for "IPv4 Address" under your WiFi adapter (e.g., `192.168.1.100`)

**Mac/Linux:**
```bash
ifconfig | grep inet
```

### 3. Start the Python Server

Make sure the server is accessible from your network:

```bash
cd "path/to/SIH_SPORTS_proj"
python app.py
```

The server runs on `http://0.0.0.0:5000` which makes it accessible from other devices.

### 4. Configure the Android App

1. Run the app on your Android device or emulator
2. Enter your computer's IP address (e.g., `192.168.1.100`)
3. Keep port as `5000`
4. Click "Test Connection" to verify
5. Select "Squat Mode" or "Jump Mode"

## For Android Emulator

If using Android Emulator, use `10.0.2.2` as the IP address (this is the emulator's alias for localhost).

## Troubleshooting

### Connection Failed
- Ensure Python server is running
- Check both devices are on same WiFi
- Verify firewall isn't blocking port 5000
- Try disabling Windows Firewall temporarily

### Stream Not Loading
- Check camera is working in web browser first
- Verify the correct IP address
- Make sure cleartext traffic is allowed (already configured)

### Black Screen
- Camera might be in use by another app
- Restart the Python server
- Check server console for errors

## Project Structure

```
android_app/
├── app/
│   ├── src/main/
│   │   ├── java/com/sih/fitnessmonitor/
│   │   │   ├── MainActivity.kt      # Home screen with connection settings
│   │   │   └── StreamActivity.kt    # Video stream display
│   │   ├── res/
│   │   │   ├── layout/              # XML layouts
│   │   │   ├── values/              # Colors, strings, themes
│   │   │   └── drawable/            # Button styles, icons
│   │   └── AndroidManifest.xml
│   └── build.gradle.kts
├── build.gradle.kts
├── settings.gradle.kts
└── README.md
```

## Features

- ✅ Connect to Flask backend server
- ✅ Test connection before streaming
- ✅ Switch between Squat and Jump modes
- ✅ Real-time MJPEG stream display
- ✅ Dark theme matching web UI
- ✅ Error handling and status display

## Building APK

1. In Android Studio: Build → Build Bundle(s) / APK(s) → Build APK(s)
2. APK will be in `app/build/outputs/apk/debug/`

## License

Part of SIH 2025 Sports Project
