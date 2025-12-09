# API Reference

## Overview

The AI Fitness Monitor server exposes a RESTful API for exercise analysis. The server supports both MJPEG streaming for web clients and JSON-based frame processing for mobile apps.

## Base URL

```
http://<server-ip>:5000
```

## Authentication

Currently, the API does not require authentication. For production deployments, consider adding API key authentication.

---

## Endpoints

### GET /

**Description**: Serves the web interface with embedded video streams.

**Response**: HTML page with exercise selection and video display.

---

### GET /squat_feed

**Description**: Returns an MJPEG video stream with real-time squat analysis overlay.

**Response Headers**:
```
Content-Type: multipart/x-mixed-replace; boundary=frame
```

**Response**: Continuous stream of JPEG frames with pose overlay and feedback.

**Usage** (HTML):
```html
<img src="/squat_feed" alt="Squat Analysis">
```

---

### GET /jump_feed

**Description**: Returns an MJPEG video stream with real-time jump analysis overlay.

**Response Headers**:
```
Content-Type: multipart/x-mixed-replace; boundary=frame
```

**Response**: Continuous stream of JPEG frames with pose overlay and jump measurements.

**Usage** (HTML):
```html
<img src="/jump_feed" alt="Jump Analysis">
```

---

### POST /process_frame

**Description**: Processes a single camera frame from mobile device and returns analysis results.

**Request Headers**:
```
Content-Type: application/json
```

**Request Body**:
```json
{
  "image": "base64_encoded_jpeg_string",
  "type": "squat" | "jump"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `image` | string | Yes | Base64-encoded JPEG image |
| `type` | string | Yes | Exercise type: "squat" or "jump" |

**Response** (Success - 200):
```json
{
  "image": "base64_encoded_result_jpeg",
  "count": 5,
  "stage": "UP",
  "feedback": "Good depth!",
  "angle": 85.5
}
```

| Field | Type | Description |
|-------|------|-------------|
| `image` | string | Processed frame with pose overlay |
| `count` | integer | Exercise repetition count |
| `stage` | string | Current exercise phase |
| `feedback` | string | Form feedback message |
| `angle` | float | Joint angle (if applicable) |

**Response** (Error - 400):
```json
{
  "error": "Missing required field: image"
}
```

**Response** (Error - 500):
```json
{
  "error": "Failed to process frame"
}
```

**Example** (cURL):
```bash
curl -X POST http://localhost:5000/process_frame \
  -H "Content-Type: application/json" \
  -d '{
    "image": "/9j/4AAQSkZJRg...",
    "type": "squat"
  }'
```

**Example** (Python):
```python
import requests
import base64
import cv2

# Capture frame
cap = cv2.VideoCapture(0)
ret, frame = cap.read()

# Encode to base64
_, buffer = cv2.imencode('.jpg', frame)
image_base64 = base64.b64encode(buffer).decode('utf-8')

# Send request
response = requests.post(
    'http://localhost:5000/process_frame',
    json={
        'image': image_base64,
        'type': 'squat'
    }
)

result = response.json()
print(f"Count: {result['count']}, Stage: {result['stage']}")
```

---

### POST /reset_analyzer

**Description**: Resets the exercise analyzer state, clearing rep count and calibration data.

**Request Headers**:
```
Content-Type: application/json
```

**Request Body**:
```json
{
  "type": "squat" | "jump"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Analyzer type to reset |

**Response** (Success - 200):
```json
{
  "status": "success",
  "message": "Squat analyzer reset"
}
```

**Example** (cURL):
```bash
curl -X POST http://localhost:5000/reset_analyzer \
  -H "Content-Type: application/json" \
  -d '{"type": "squat"}'
```

---

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid input |
| 404 | Not Found - Endpoint doesn't exist |
| 500 | Internal Server Error |

---

## Rate Limits

For optimal performance, limit frame processing requests to:
- **Maximum**: 30 frames per second
- **Recommended**: 15-20 frames per second

---

## WebSocket Support (Future)

WebSocket support for lower latency is planned for future releases.

```javascript
// Future API
const ws = new WebSocket('ws://localhost:5000/ws');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Rep count:', data.count);
};
```

---

## Data Types

### Exercise Type
```typescript
type ExerciseType = "squat" | "jump";
```

### Squat Stages
```typescript
type SquatStage = "STANDING" | "DESCENDING" | "BOTTOM" | "ASCENDING";
```

### Jump Stages
```typescript
type JumpStage = "READY" | "TAKEOFF" | "AIRBORNE" | "LANDING";
```
