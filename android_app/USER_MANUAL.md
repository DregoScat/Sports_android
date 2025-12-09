# AI Fitness Monitor - User Manual

**Version:** 1.0  
**Last Updated:** December 9, 2025  
**Platform:** Android 7.0 (API 24) and above

---

## Table of Contents

1. [Introduction](#introduction)
2. [System Requirements](#system-requirements)
3. [Installation Guide](#installation-guide)
4. [Initial Setup & Configuration](#initial-setup--configuration)
5. [User Interface Overview](#user-interface-overview)
6. [Features](#features)
7. [Using the Application](#using-the-application)
8. [Troubleshooting](#troubleshooting)
9. [FAQs](#faqs)
10. [Best Practices](#best-practices)
11. [Privacy & Permissions](#privacy--permissions)
12. [Support & Contact](#support--contact)

---

## Introduction

**AI Fitness Monitor** is an intelligent fitness tracking application that uses artificial intelligence to analyze your exercise form in real-time. The app connects to a backend server running pose detection algorithms to provide instant feedback on your squat and jump exercises.

### Key Features
- 🏋️ **Real-time Squat Analysis** - Counts correct and incorrect squats with form feedback
- 🦘 **Jump Height Measurement** - Measures vertical jump height in pixels/inches
- 📱 **Device Camera Integration** - Uses your phone's camera for pose detection
- 🔄 **Front/Back Camera Support** - Switch between cameras for optimal positioning
- 💬 **Live Feedback** - Instant visual feedback on exercise form

---

## System Requirements

### Android Device Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Android Version | 7.0 (Nougat) | 10.0 or higher |
| RAM | 2 GB | 4 GB or more |
| Storage | 50 MB free space | 100 MB free space |
| Camera | Rear camera required | Front + Rear camera |
| Network | WiFi or Mobile Data | WiFi (for stability) |

### Server Requirements

The app requires a running backend server with:
- Python 3.8+ with Flask
- MediaPipe for pose detection
- OpenCV for image processing
- Network accessibility from your Android device

---

## Installation Guide

### Method 1: Install from APK File

1. **Enable Unknown Sources**
   - Go to **Settings** → **Security** (or **Privacy**)
   - Enable **Install unknown apps** for your file manager
   - On newer Android versions: **Settings** → **Apps** → **Special access** → **Install unknown apps**

2. **Transfer the APK**
   - Copy `FitnessMonitor.apk` to your Android device via:
     - USB cable
     - Cloud storage (Google Drive, Dropbox)
     - Email attachment
     - Direct download

3. **Install the Application**
   - Open your file manager
   - Navigate to the APK file location
   - Tap on `FitnessMonitor.apk`
   - Tap **Install** when prompted
   - Wait for installation to complete
   - Tap **Open** or find the app in your app drawer

### Method 2: Install via ADB (Developer Mode)

```bash
# Connect your device via USB with debugging enabled
adb install FitnessMonitor.apk
```

---

## Initial Setup & Configuration

### Step 1: Launch the Application

1. Find **AI Fitness Monitor** in your app drawer
2. Tap the app icon to launch

### Step 2: Configure Server Connection

On the main screen, you'll see the **Server Configuration** section:

1. **Server IP Address**
   - Enter the IP address of your backend server
   - Default: `10.0.2.2` (Android emulator localhost)
   - Example: `192.168.1.100`
   
   > 💡 **Tip:** To find your server's IP address:
   > - Windows: Run `ipconfig` in Command Prompt
   > - Mac/Linux: Run `ifconfig` or `ip addr` in Terminal

2. **Port Number**
   - Enter the server port (default: `5000`)
   - Must match the port your Flask server is running on

### Step 3: Test Connection

1. Tap the **Test Connection** button
2. Wait for the connection test to complete
3. Check the status indicator:
   - ✅ **Green "Connected"** - Server is reachable
   - ❌ **Red "Disconnected"** - Check server/network settings

### Step 4: Grant Permissions

When prompted, allow the following permissions:
- **Camera** - Required for capturing exercise video
- The app will not function without camera permission

---

## User Interface Overview

### Main Screen (Home)

```
┌─────────────────────────────────┐
│     AI Fitness Monitor          │
│   Connect to your fitness server│
├─────────────────────────────────┤
│  ┌───────────────────────────┐  │
│  │  Server Configuration     │  │
│  │                           │  │
│  │  Server IP Address        │  │
│  │  [192.168.1.100        ]  │  │
│  │                           │  │
│  │  Port                     │  │
│  │  [5000                 ]  │  │
│  │                           │  │
│  │  [  Test Connection    ]  │  │
│  │                           │  │
│  │  Status: Connected ✓      │  │
│  └───────────────────────────┘  │
├─────────────────────────────────┤
│  ┌─────────┐    ┌─────────┐    │
│  │  SQUAT  │    │  JUMP   │    │
│  │  MODE   │    │  MODE   │    │
│  └─────────┘    └─────────┘    │
└─────────────────────────────────┘
```

| Element | Description |
|---------|-------------|
| Server IP | Input field for backend server IP address |
| Port | Input field for server port number |
| Test Connection | Button to verify server connectivity |
| Status | Shows current connection state |
| Squat Mode | Starts squat analysis session |
| Jump Mode | Starts jump analysis session |

### Stream Screen (Exercise View)

```
┌─────────────────────────────────┐
│ [←] Squat Analysis    Status [📷]│
├─────────────────────────────────┤
│                                 │
│   ┌─────────────────────────┐   │
│   │                         │   │
│   │    Camera Feed /        │   │
│   │    Processed Video      │   │
│   │                         │   │
│   │  [Pose skeleton overlay]│   │
│   │                         │   │
│   └─────────────────────────┘   │
│                                 │
├─────────────────────────────────┤
│  [  SQUAT  ]    [  JUMP  ]     │
└─────────────────────────────────┘
```

| Element | Description |
|---------|-------------|
| ← (Back) | Return to main screen |
| Title | Shows current analysis mode |
| Status | Connection/streaming status |
| 📷 (Camera Switch) | Toggle front/back camera |
| Video Feed | Live camera with pose overlay |
| Mode Buttons | Switch between squat/jump analysis |

---

## Features

### 1. Squat Analysis Mode

The squat analyzer tracks your squat form and provides real-time feedback.

**Metrics Displayed:**
- **CORRECT** - Count of properly executed squats
- **INCORRECT** - Count of improper squats
- **STAGE** - Current squat phase (S1, S2, S3)

**Squat Stages:**
| Stage | Description | Knee Angle |
|-------|-------------|------------|
| S1 | Standing position | > 160° |
| S2 | Partial squat | 95° - 160° |
| S3 | Full squat depth | ≤ 95° |

**Feedback Messages:**
| Message | Meaning |
|---------|---------|
| "Correct Squat" | Proper form completed |
| "Incomplete Squat" | Didn't reach full depth |
| "Hold at bottom longer" | Need more time at S3 |
| "Bend forward" | Back angle too upright |
| "Bend backwards" | Leaning too far forward |
| "Lower your hips" | Not deep enough |
| "Squat too deep" | Over-extended squat |
| "Knees over toes" | Knee position warning |

### 2. Jump Analysis Mode

The jump analyzer measures your vertical jump height and tracks jump count.

**Metrics Displayed:**
- **JUMPS** - Total number of jumps detected
- **MAX HEIGHT** - Highest jump recorded (in pixels)
- **Current Height** - Real-time jump measurement

**Instructions:**
1. Stand in view of the camera
2. Raise your **right hand to your nose** to ARM the system
3. Perform your jump when "Armed" is displayed
4. Raise your **left hand to your nose** to RESET

### 3. Camera Switching

Toggle between front and back cameras:
- Tap the **camera icon** (📷) in the top-right corner
- Front camera: Good for facing the phone (mirror view)
- Back camera: Better for third-party recording or tripod setup

---

## Using the Application

### Starting a Squat Session

1. **Connect to Server**
   - Enter server IP and port on main screen
   - Test connection to verify

2. **Start Squat Mode**
   - Tap **SQUAT MODE** button
   - Grant camera permission if prompted

3. **Position Yourself**
   - Stand 6-10 feet from the camera
   - Ensure your full body is visible
   - Good lighting improves accuracy

4. **Perform Squats**
   - Stand straight (S1 stage)
   - Lower into squat position
   - Hold at bottom (S3 stage) for 3+ frames
   - Return to standing
   - Watch feedback at bottom of screen

5. **End Session**
   - Tap back arrow (←) to return to main screen

### Starting a Jump Session

1. **Connect to Server**
   - Same as squat session

2. **Start Jump Mode**
   - Tap **JUMP MODE** button

3. **Arm the System**
   - Stand still facing the camera
   - Raise your **right hand to your nose**
   - Wait for "Armed: ready to measure" message

4. **Perform Jump**
   - Jump vertically
   - Land naturally
   - View your jump height result

5. **Reset for Another Jump**
   - Raise your **left hand to your nose** to reset
   - Re-arm by raising right hand to nose

---

## Troubleshooting

### Connection Issues

| Problem | Solution |
|---------|----------|
| "Connection Error" | 1. Verify server is running<br>2. Check IP address is correct<br>3. Ensure same WiFi network<br>4. Check firewall settings |
| "Server Error: 500" | Server-side error - check server logs |
| "Server Error: 404" | Wrong endpoint - verify server version |
| Frequent disconnects | Use WiFi instead of mobile data |

### Camera Issues

| Problem | Solution |
|---------|----------|
| Black screen | 1. Grant camera permission<br>2. Close other camera apps<br>3. Restart the app |
| Laggy video | 1. Improve lighting<br>2. Move closer to WiFi router<br>3. Reduce background apps |
| Camera won't switch | 1. Verify device has front camera<br>2. Restart the app |
| "Camera permission required" | Go to Settings → Apps → AI Fitness Monitor → Permissions → Enable Camera |

### Pose Detection Issues

| Problem | Solution |
|---------|----------|
| "Full body not visible" | Move back from camera, ensure full body in frame |
| Incorrect counts | 1. Improve lighting<br>2. Wear contrasting clothing<br>3. Avoid busy backgrounds |
| Skeleton not showing | Server processing delay - check connection |

### Performance Issues

| Problem | Solution |
|---------|----------|
| App crashes | 1. Clear app cache<br>2. Free up device memory<br>3. Reinstall app |
| High battery drain | 1. Reduce session length<br>2. Lower screen brightness<br>3. Use rear camera (less processing) |
| Overheating | 1. Take breaks between sessions<br>2. Remove phone case<br>3. Avoid direct sunlight |

---

## FAQs

### General Questions

**Q: Do I need an internet connection to use the app?**
> A: Yes, the app requires network connectivity to communicate with the backend server for pose detection processing.

**Q: Can I use the app offline?**
> A: No, the AI processing happens on the server. Without server connectivity, the app cannot analyze your exercises.

**Q: How accurate is the pose detection?**
> A: Accuracy depends on lighting, camera quality, clothing contrast, and distance. Under good conditions, accuracy is typically 90%+.

**Q: Does the app store my video data?**
> A: No, video frames are processed in real-time and not stored on the server or device.

### Technical Questions

**Q: What is the default server port?**
> A: The default port is `5000`. This can be configured in the app settings.

**Q: Can multiple devices connect to one server?**
> A: Yes, the server supports multiple simultaneous connections, though performance may vary.

**Q: Why does the app need camera permission?**
> A: Camera access is required to capture video frames for pose detection analysis.

**Q: What happens if I lose connection mid-session?**
> A: The app will show a connection error and attempt to reconnect. Your current session counts are preserved.

### Exercise Questions

**Q: Why is my squat marked as incorrect?**
> A: Common reasons include:
> - Not reaching full depth (knee angle > 95°)
> - Not holding at bottom long enough
> - Poor form (back angle, knee position)

**Q: How do I improve my jump measurement accuracy?**
> A: 
> - Ensure good lighting
> - Stand still when arming
> - Wait for "Armed" confirmation before jumping
> - Land in the same position you started

---

## Best Practices

### For Best Results

1. **Optimal Camera Setup**
   - Place phone on stable surface or tripod
   - Position camera at waist height
   - Maintain 6-10 feet distance
   - Use landscape or portrait consistently

2. **Lighting Recommendations**
   - Use well-lit areas
   - Avoid direct sunlight behind you
   - Avoid shadows on your body
   - Natural light works best

3. **Clothing Tips**
   - Wear fitted (not baggy) clothing
   - Choose colors that contrast with background
   - Avoid patterns that may confuse detection

4. **Environment Setup**
   - Use plain, uncluttered backgrounds
   - Ensure clear floor space
   - Remove mirrors that may cause reflections

### Network Optimization

1. **WiFi Connection**
   - Connect to 5GHz network when available
   - Stay within good range of router
   - Minimize other devices on network during use

2. **Server Proximity**
   - Run server on same local network
   - Minimize network hops
   - Use wired connection for server

### Session Management

1. **Before Starting**
   - Test connection first
   - Warm up before exercises
   - Verify full body is visible

2. **During Session**
   - Watch feedback messages
   - Adjust position as needed
   - Take breaks if app slows down

3. **After Session**
   - Return to main screen properly
   - Close app when not in use
   - Note your progress

---

## Privacy & Permissions

### Required Permissions

| Permission | Purpose | Required |
|------------|---------|----------|
| Camera | Capture video for pose analysis | Yes |
| Internet | Communicate with backend server | Yes |
| Network State | Check connectivity status | Yes |

### Data Handling

- **Video Data**: Processed in real-time, not stored
- **Personal Data**: No personal information collected
- **Analytics**: No usage tracking or analytics
- **Third Parties**: No data shared with third parties

### Security Notes

- Use trusted networks (avoid public WiFi)
- Server communication uses HTTP (configure HTTPS for production)
- No authentication required by default

---

## Support & Contact

### Getting Help

1. **Check this manual** for common issues
2. **Review troubleshooting section** above
3. **Check server logs** for backend issues

### Reporting Bugs

When reporting issues, please include:
- Device model and Android version
- App version
- Steps to reproduce the issue
- Error messages (if any)
- Screenshots (if applicable)

### Project Information

- **Project:** AI Fitness Monitor (SIH 2025)
- **Repository:** [GitHub - NYN-05/SIH_SQUATS](https://github.com/NYN-05/SIH_SQUATS)
- **Branch:** main

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Dec 2025 | Initial release with squat and jump analysis |

---

## Appendix

### Server Setup Quick Reference

```bash
# Navigate to project directory
cd SIH_SPORTS_proj

# Activate virtual environment
.\venv\Scripts\Activate.ps1  # Windows
source venv/bin/activate      # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run server
python app.py
```

Server will start at `http://0.0.0.0:5000`

### Keyboard Shortcuts (Development)

| Key | Action |
|-----|--------|
| Q | Quit standalone Python scripts |
| ESC | Close OpenCV windows |

---

*© 2025 AI Fitness Monitor Team. All rights reserved.*
