# Builds Directory

This folder contains pre-built APK files for the Android application.

## Files

- `FitnessMonitor.apk` - Release build of the fitness monitor Android app

## Installation

1. Transfer the APK to your Android device
2. Enable "Install from unknown sources" in device settings
3. Open the APK file to install

## Building from Source

To build the APK from source:

```bash
cd android_app
./gradlew assembleRelease
```

The APK will be generated at:
`android_app/app/build/outputs/apk/release/app-release.apk`
