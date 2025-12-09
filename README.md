# AI Fitness Monitor

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.2.5-green.svg)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.x-orange.svg)
![Android](https://img.shields.io/badge/Android-7.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**Real-time AI-powered fitness monitoring system using pose estimation**

[Features](#features) • [Installation](#installation) • [Usage](#usage) • [API](#api) • [Architecture](#architecture) • [Contributing](#contributing)

</div>

---

## 🎯 Overview

AI Fitness Monitor is a comprehensive fitness tracking system that uses computer vision and machine learning to analyze exercise form in real-time. The system consists of a Python server with pose detection capabilities and an Android mobile application for user interaction.

### Key Features

- **Real-time Squat Analysis**: Tracks squat depth, knee angles, and form with instant feedback
- **Vertical Jump Measurement**: Measures jump height using pose estimation
- **Voice Feedback**: Audio cues to guide proper exercise form
- **Mobile Integration**: Android app for convenient mobile workout tracking
- **WebSocket Streaming**: Low-latency video processing for smooth experience

---

## 📁 Project Structure

```
SIH_SPORTS_proj/
├── server/                     # Python backend server
│   ├── src/
│   │   ├── analyzers/         # Exercise analysis modules
│   │   │   ├── squat_analyzer.py
│   │   │   └── jump_analyzer.py
│   │   ├── api/               # Flask API routes
│   │   │   └── routes.py
│   │   └── utils/             # Utility modules
│   │       ├── camera_manager.py
│   │       └── frame_processor.py
│   ├── config/                # Configuration files
│   │   └── settings.py
│   ├── templates/             # HTML templates
│   ├── tests/                 # Unit & integration tests
│   ├── requirements.txt       # Python dependencies
│   └── run.py                 # Main entry point
│
├── android_app/               # Android mobile application
│   ├── app/src/main/
│   │   ├── java/             # Kotlin source code
│   │   └── res/              # Android resources
│   ├── build.gradle.kts      # Gradle build config
│   └── USER_MANUAL.md        # User documentation
│
├── builds/                    # Pre-built APK files
│   └── FitnessMonitor.apk
│
├── docs/                      # Additional documentation
│   ├── API.md                # API reference
│   └── ARCHITECTURE.md       # System architecture
│
└── README.md                  # This file
```

---

## 🚀 Installation

### Prerequisites

- **Python 3.8+** with pip
- **Android Studio** (for Android development)
- **Webcam** (for local testing)

### Server Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-repo/ai-fitness-monitor.git
   cd ai-fitness-monitor
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/macOS
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   cd server
   pip install -r requirements.txt
   ```

4. **Run the server**
   ```bash
   python run.py
   ```

   The server will start at `http://0.0.0.0:5000`

### Android App Setup

1. **Install pre-built APK**
   - Transfer `builds/FitnessMonitor.apk` to your Android device
   - Enable "Install from unknown sources"
   - Install the APK

2. **Or build from source**
   ```bash
   cd android_app
   ./gradlew assembleDebug
   ```

---

## 📱 Usage

### Quick Start

1. **Start the server** on your computer
2. **Connect your phone** to the same WiFi network
3. **Open the app** and enter the server IP address
4. **Select exercise type** (Squat or Jump)
5. **Position yourself** in the camera frame
6. **Start exercising** and get real-time feedback!

### Server Modes

- **Webcam Mode**: Uses your computer's webcam
- **Mobile Mode**: Processes frames from the Android app

### Exercise Guidelines

#### Squats
- Stand 6-8 feet from camera
- Ensure full body is visible
- Listen for voice feedback on depth

#### Vertical Jumps
- Stand still for calibration
- Jump straight up
- Wait for height measurement

---

## 🔌 API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Web interface |
| GET | `/squat_feed` | MJPEG squat analysis stream |
| GET | `/jump_feed` | MJPEG jump analysis stream |
| POST | `/process_frame` | Process mobile camera frame |
| POST | `/reset_analyzer` | Reset analyzer state |

### POST /process_frame

**Request:**
```json
{
  "image": "base64_encoded_jpeg",
  "type": "squat" | "jump"
}
```

**Response:**
```json
{
  "image": "base64_encoded_result",
  "count": 5,
  "stage": "UP",
  "feedback": "Good form!"
}
```

---

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Android   │────▶│   Flask     │────▶│  MediaPipe  │
│     App     │◀────│   Server    │◀────│    Pose     │
└─────────────┘     └─────────────┘     └─────────────┘
      │                    │                    │
      │   HTTP/WebSocket   │    Pose Detection  │
      │                    │                    │
      ▼                    ▼                    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Camera    │     │   OpenCV    │     │   Numpy     │
│   Frame     │     │  Processing │     │   Arrays    │
└─────────────┘     └─────────────┘     └─────────────┘
```

### Key Components

- **MediaPipe Pose**: Google's ML model for body pose estimation
- **OpenCV**: Image processing and video capture
- **Flask**: Lightweight web framework for API
- **pyttsx3**: Offline text-to-speech for voice feedback

---

## 🧪 Testing

```bash
cd server

# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_analyzers.py -v
```

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [MediaPipe](https://mediapipe.dev/) - Pose detection model
- [OpenCV](https://opencv.org/) - Computer vision library
- [Flask](https://flask.palletsprojects.com/) - Web framework

---

<div align="center">

**Made with ❤️ for SIH 2025**

</div>
