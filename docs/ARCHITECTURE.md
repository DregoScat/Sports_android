# System Architecture

## Overview

The AI Fitness Monitor system uses a client-server architecture with real-time pose estimation for exercise analysis.

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                              │
├─────────────────┬─────────────────┬─────────────────────────┤
│   Android App   │   Web Browser   │    Future Clients       │
│   (Kotlin)      │   (HTML/JS)     │    (iOS, Desktop)       │
└────────┬────────┴────────┬────────┴─────────────────────────┘
         │                 │
         │    HTTP/REST    │    MJPEG Stream
         │                 │
         ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    API LAYER                                 │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                  Flask Server                           │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │ │
│  │  │   /         │  │ /process_    │  │ /squat_feed  │  │ │
│  │  │   (index)   │  │   frame      │  │ /jump_feed   │  │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    PROCESSING LAYER                          │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │               Frame Processor                            ││
│  │  ┌──────────────────┐  ┌──────────────────────────────┐ ││
│  │  │  Camera Manager  │  │   Mobile Frame Processor     │ ││
│  │  │  (Webcam Input)  │  │   (Base64 Decode/Encode)     │ ││
│  │  └────────┬─────────┘  └──────────────┬───────────────┘ ││
│  │           │                           │                  ││
│  │           └───────────┬───────────────┘                  ││
│  │                       ▼                                  ││
│  │  ┌────────────────────────────────────────────────────┐ ││
│  │  │              OpenCV Processing                      │ ││
│  │  │   - Frame decoding/encoding                         │ ││
│  │  │   - Image transformations                           │ ││
│  │  │   - Overlay rendering                               │ ││
│  │  └────────────────────────────────────────────────────┘ ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    ANALYSIS LAYER                            │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │               Exercise Analyzers                         ││
│  │  ┌────────────────────┐  ┌────────────────────────────┐ ││
│  │  │   Squat Analyzer   │  │      Jump Analyzer         │ ││
│  │  │  - Rep counting    │  │  - Height measurement      │ ││
│  │  │  - Depth tracking  │  │  - Takeoff detection       │ ││
│  │  │  - Form feedback   │  │  - Landing detection       │ ││
│  │  └────────┬───────────┘  └──────────────┬─────────────┘ ││
│  │           └───────────┬─────────────────┘               ││
│  │                       ▼                                  ││
│  │  ┌────────────────────────────────────────────────────┐ ││
│  │  │              MediaPipe Pose                         │ ││
│  │  │   - 33 body landmarks                               │ ││
│  │  │   - Real-time inference                             │ ││
│  │  │   - GPU acceleration                                │ ││
│  │  └────────────────────────────────────────────────────┘ ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FEEDBACK LAYER                            │
│                                                              │
│  ┌────────────────────┐  ┌────────────────────────────────┐ │
│  │  Visual Overlay    │  │      Voice Feedback            │ │
│  │  - Skeleton draw   │  │  - pyttsx3 TTS engine          │ │
│  │  - Angle display   │  │  - Async speech thread         │ │
│  │  - Status text     │  │  - Form correction cues        │ │
│  └────────────────────┘  └────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Client Layer

#### Android App
- **Technology**: Kotlin, CameraX 1.3.1
- **Responsibilities**:
  - Camera capture and frame encoding
  - Server communication via OkHttp
  - UI rendering with Jetpack components
  - Local storage for settings

#### Web Browser
- **Technology**: HTML5, JavaScript
- **Responsibilities**:
  - MJPEG stream display
  - Exercise selection UI
  - Server status monitoring

---

### 2. API Layer

#### Flask Server
- **Technology**: Flask 2.2.5, Python 3.8+
- **Endpoints**:
  - `GET /` - Web interface
  - `GET /squat_feed` - MJPEG squat stream
  - `GET /jump_feed` - MJPEG jump stream
  - `POST /process_frame` - Mobile frame processing
  - `POST /reset_analyzer` - Reset analyzer state

#### Route Blueprint
```python
from flask import Blueprint
api_bp = Blueprint('api', __name__)

@api_bp.route('/process_frame', methods=['POST'])
def process_frame():
    # Frame processing logic
    pass
```

---

### 3. Processing Layer

#### Camera Manager
- **Purpose**: Thread-safe webcam access
- **Features**:
  - Singleton pattern
  - Lazy initialization
  - Analyzer switching

```python
class CameraManager:
    _instance = None
    _lock = threading.Lock()
    
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance
```

#### Mobile Frame Processor
- **Purpose**: Process Base64 frames from mobile app
- **Features**:
  - Base64 decoding
  - JPEG encoding
  - Analyzer routing

---

### 4. Analysis Layer

#### Squat Analyzer
- **State Machine**:
  ```
  STANDING → DESCENDING → BOTTOM → ASCENDING → STANDING
  ```
- **Metrics**:
  - Knee angle (degrees)
  - Hip angle (degrees)
  - Depth percentage
  - Rep count

#### Jump Analyzer
- **State Machine**:
  ```
  READY → TAKEOFF → AIRBORNE → LANDING → READY
  ```
- **Metrics**:
  - Standing height (calibration)
  - Jump height (cm)
  - Hang time (ms)

#### MediaPipe Pose
- **Model**: BlazePose GHUM 3D
- **Landmarks**: 33 body keypoints
- **Performance**: ~30 FPS on CPU

```python
import mediapipe as mp

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
```

---

### 5. Feedback Layer

#### Visual Overlay
- **Technology**: OpenCV
- **Features**:
  - Skeleton rendering
  - Joint angle display
  - Status indicators
  - Rep counter

#### Voice Feedback
- **Technology**: pyttsx3
- **Features**:
  - Offline TTS
  - Async speech (non-blocking)
  - Form correction cues

```python
import pyttsx3
import threading

def speak_async(text):
    def _speak():
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
    threading.Thread(target=_speak, daemon=True).start()
```

---

## Data Flow

### Mobile Frame Processing

```
┌───────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐
│  Camera   │────▶│  Encode   │────▶│   HTTP    │────▶│  Server   │
│  (Phone)  │     │  Base64   │     │   POST    │     │  Flask    │
└───────────┘     └───────────┘     └───────────┘     └─────┬─────┘
                                                            │
                                                            ▼
┌───────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐
│  Display  │◀────│  Decode   │◀────│  HTTP     │◀────│  Process  │
│  (Phone)  │     │  Base64   │     │  Response │     │  Frame    │
└───────────┘     └───────────┘     └───────────┘     └───────────┘
```

### Webcam Streaming

```
┌───────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐
│  Webcam   │────▶│  Capture  │────▶│  Analyze  │────▶│   MJPEG   │
│           │     │  Frame    │     │  Overlay  │     │   Stream  │
└───────────┘     └───────────┘     └───────────┘     └─────┬─────┘
                                                            │
                                                            ▼
                                                      ┌───────────┐
                                                      │  Browser  │
                                                      │  Display  │
                                                      └───────────┘
```

---

## Deployment Architecture

### Development
```
┌─────────────────────────────────────────┐
│            Development Machine           │
│  ┌─────────────┐    ┌─────────────────┐ │
│  │   Flask     │    │     Webcam      │ │
│  │   Server    │◀───│     Input       │ │
│  │   :5000     │    │                 │ │
│  └──────┬──────┘    └─────────────────┘ │
│         │                               │
└─────────┼───────────────────────────────┘
          │
          │ Same Network
          ▼
    ┌───────────┐
    │  Android  │
    │   Phone   │
    └───────────┘
```

### Production
```
┌─────────────────────────────────────────┐
│            Cloud Server (Azure)          │
│  ┌─────────────┐    ┌─────────────────┐ │
│  │   Gunicorn  │    │    Nginx        │ │
│  │   Workers   │◀───│    Reverse      │ │
│  │             │    │    Proxy        │ │
│  └─────────────┘    └────────┬────────┘ │
│                              │          │
└──────────────────────────────┼──────────┘
                               │
                               │ HTTPS
                               ▼
                        ┌─────────────┐
                        │   Clients   │
                        │ (Mobile/Web)│
                        └─────────────┘
```

---

## Security Considerations

1. **Input Validation**: All Base64 inputs validated before processing
2. **Frame Size Limits**: Maximum 5MB per frame to prevent DoS
3. **HTTPS**: Recommended for production deployments
4. **Authentication**: API keys for production (not implemented in v1)
5. **Rate Limiting**: Prevent abuse with request throttling

---

## Performance Optimization

1. **Lazy Initialization**: MediaPipe loaded on first use
2. **Frame Skipping**: Drop frames under high load
3. **JPEG Quality**: Adjustable compression (default: 80%)
4. **Thread Pooling**: Gunicorn workers for concurrent requests
5. **GPU Acceleration**: MediaPipe uses GPU when available

---

## Future Enhancements

1. **WebSocket Support**: Lower latency communication
2. **Exercise Library**: Additional exercises (pushups, planks)
3. **User Profiles**: Progress tracking and history
4. **Cloud Storage**: Exercise session recordings
5. **ML Model Training**: Custom pose models for accuracy
