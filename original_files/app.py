import threading
import time
import cv2
import numpy as np
from flask import Flask, Response, render_template_string, request, jsonify
import base64

from jump import JumpAnalyzer
from squats import SquatAnalyzer

app = Flask(__name__)

# Mobile frame processor for Android camera frames
class MobileFrameProcessor:
    def __init__(self):
        self.squat_analyzer = None
        self.jump_analyzer = None
        self.lock = threading.Lock()
    
    def get_squat_analyzer(self):
        with self.lock:
            if self.squat_analyzer is None:
                # Create analyzer without camera
                self.squat_analyzer = SquatAnalyzerMobile()
            return self.squat_analyzer
    
    def get_jump_analyzer(self):
        with self.lock:
            if self.jump_analyzer is None:
                self.jump_analyzer = JumpAnalyzerMobile()
            return self.jump_analyzer

mobile_processor = MobileFrameProcessor()


class SquatAnalyzerMobile:
    """Squat analyzer that processes frames without camera access"""
    def __init__(self):
        import mediapipe as mp
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose()
        self.drawing_utils = mp.solutions.drawing_utils
        self.correct_counter = 0
        self.incorrect_counter = 0
        self.stage = None
        self.sequence = []
        self.feedback = None
        from collections import deque
        self.knee_history = deque(maxlen=5)
        self.back_history = deque(maxlen=5)
        self.depth_hold = 0
        self.min_knee_angle = 180

    @staticmethod
    def _calculate_angle(a, b, c):
        a = np.array(a)
        b = np.array(b)
        c = np.array(c)
        radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(
            a[1] - b[1], a[0] - b[0]
        )
        angle = np.abs(radians * 180.0 / np.pi)
        if angle > 180.0:
            angle = 360 - angle
        return angle

    def _get_landmark(self, landmarks, name: str):
        lm = landmarks[self.mp_pose.PoseLandmark[name].value]
        return [lm.x, lm.y, lm.visibility]

    def process_frame(self, frame):
        """Process a single frame and return annotated image"""
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = self.pose.process(image)
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            shoulder = self._get_landmark(landmarks, "LEFT_SHOULDER")
            hip = self._get_landmark(landmarks, "LEFT_HIP")
            knee = self._get_landmark(landmarks, "LEFT_KNEE")
            ankle = self._get_landmark(landmarks, "LEFT_ANKLE")

            if all(lm[2] > 0.8 for lm in [shoulder, hip, knee, ankle]):
                knee_angle = self._calculate_angle(hip, knee, ankle)
                back_angle = self._calculate_angle(shoulder, hip, knee)
                self.knee_history.append(knee_angle)
                self.back_history.append(back_angle)
                smooth_knee = sum(self.knee_history) / len(self.knee_history)
                smooth_back = sum(self.back_history) / len(self.back_history)
                knee_angle = smooth_knee
                back_angle = smooth_back
                self.min_knee_angle = min(self.min_knee_angle, knee_angle)

                frame_h, frame_w = image.shape[:2]
                cv2.putText(image, f"Knee: {int(knee_angle)}",
                    tuple(np.multiply(knee[:2], [frame_w, frame_h]).astype(int)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.putText(image, f"Back: {int(back_angle)}",
                    tuple(np.multiply(hip[:2], [frame_w, frame_h]).astype(int)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)

                prev_stage = self.stage
                if knee_angle > 160:
                    self.stage = "S1"
                elif 160 >= knee_angle > 95:
                    self.stage = "S2"
                elif knee_angle <= 95:
                    self.stage = "S3"

                if self.stage and prev_stage != self.stage:
                    self.sequence.append(self.stage)

                if self.stage == "S3":
                    self.depth_hold += 1
                # Don't reset depth_hold here - let it persist until squat is counted

                feedback = None
                # Check for correct squat - sequence S1->S2->S3 and held depth
                if len(self.sequence) >= 3 and self.sequence[-3:] == ["S1", "S2", "S3"] and self.depth_hold >= 3:
                    # Moving back up from S3
                    if knee_angle > 100:  # Rising from squat
                        self.correct_counter += 1
                        feedback = "Correct Squat"
                        self.sequence = []
                        self.min_knee_angle = 180
                        self.depth_hold = 0
                elif (len(self.sequence) >= 3 and self.sequence[-3:] == ["S2", "S3", "S2"]
                        and self.depth_hold >= 3):
                    self.correct_counter += 1
                    feedback = "Correct Squat"
                    self.sequence = []
                    self.min_knee_angle = 180
                    self.depth_hold = 0
                elif len(self.sequence) >= 3 and self.sequence[-1] == "S1":
                    if self.sequence != ["S1"] and "S3" not in self.sequence:
                        self.incorrect_counter += 1
                        feedback = "Incomplete Squat - Go deeper"
                    elif self.sequence != ["S1"]:
                        # Completed squat cycle through S1 at the end
                        if self.depth_hold < 3:
                            self.incorrect_counter += 1
                            feedback = "Hold at bottom longer"
                    self.sequence = []
                    self.depth_hold = 0

                if back_angle < 25:
                    feedback = "Bend forward"
                elif back_angle > 50:
                    feedback = "Bend backwards"
                elif self.stage == "S2" and knee_angle > 80:
                    feedback = "Lower your hips"
                elif self.stage == "S3" and knee_angle < 50:
                    feedback = "Squat too deep"
                elif self.stage == "S3" and self.min_knee_angle > 60:
                    feedback = "Raise deeper"
                if ankle[0] > knee[0]:
                    feedback = "Knees over toes"
                self.feedback = feedback
            else:
                self.feedback = "Please make your full body visible"
        else:
            self.feedback = "Please make your full body visible"

        # Draw UI overlay
        cv2.rectangle(image, (0, 0), (350, 73), (245, 117, 16), -1)
        cv2.putText(image, "CORRECT", (15, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(image, str(self.correct_counter), (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(image, "INCORRECT", (120, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(image, str(self.incorrect_counter), (125, 60), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(image, "STAGE", (250, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        stage_text = self.stage if self.stage else "N/A"
        cv2.putText(image, stage_text, (245, 60), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 2, cv2.LINE_AA)

        if self.feedback:
            frame_h, frame_w = image.shape[:2]
            cv2.rectangle(image, (0, frame_h - 60), (frame_w, frame_h), (0, 0, 0), -1)
            cv2.putText(image, self.feedback, (20, frame_h - 20), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 2, cv2.LINE_AA)

        if results.pose_landmarks:
            self.drawing_utils.draw_landmarks(image, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS,
                self.drawing_utils.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=2),
                self.drawing_utils.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2))

        return image


class JumpAnalyzerMobile:
    """Jump analyzer that processes frames without camera access"""
    def __init__(self):
        import mediapipe as mp
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose()
        self.drawing_utils = mp.solutions.drawing_utils
        self.baseline_y = None
        self.max_jump_height = 0
        self.jump_count = 0
        self.is_jumping = False
        self.current_jump_height = 0
        self.feedback = None
        from collections import deque
        self.y_history = deque(maxlen=5)

    def process_frame(self, frame):
        """Process a single frame and return annotated image"""
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = self.pose.process(image)
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            left_ankle = landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE.value]
            right_ankle = landmarks[self.mp_pose.PoseLandmark.RIGHT_ANKLE.value]
            
            if left_ankle.visibility > 0.7 and right_ankle.visibility > 0.7:
                avg_ankle_y = (left_ankle.y + right_ankle.y) / 2
                self.y_history.append(avg_ankle_y)
                smooth_y = sum(self.y_history) / len(self.y_history)
                
                if self.baseline_y is None:
                    self.baseline_y = smooth_y
                
                frame_h, frame_w = image.shape[:2]
                jump_pixels = (self.baseline_y - smooth_y) * frame_h
                
                if jump_pixels > 30:  # Threshold for jump detection
                    if not self.is_jumping:
                        self.is_jumping = True
                        self.jump_count += 1
                    self.current_jump_height = max(self.current_jump_height, jump_pixels)
                    self.max_jump_height = max(self.max_jump_height, jump_pixels)
                    self.feedback = f"Jump Height: {int(self.current_jump_height)} px"
                else:
                    if self.is_jumping:
                        self.is_jumping = False
                        self.current_jump_height = 0
                    self.feedback = "Ready to jump"
                    # Update baseline when standing
                    self.baseline_y = smooth_y * 0.1 + self.baseline_y * 0.9
            else:
                self.feedback = "Please make your full body visible"
        else:
            self.feedback = "Please make your full body visible"

        # Draw UI overlay
        cv2.rectangle(image, (0, 0), (350, 73), (16, 117, 245), -1)
        cv2.putText(image, "JUMPS", (15, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(image, str(self.jump_count), (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(image, "MAX HEIGHT", (120, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(image, f"{int(self.max_jump_height)}px", (120, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2, cv2.LINE_AA)

        if self.feedback:
            frame_h, frame_w = image.shape[:2]
            cv2.rectangle(image, (0, frame_h - 60), (frame_w, frame_h), (0, 0, 0), -1)
            cv2.putText(image, self.feedback, (20, frame_h - 20), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 2, cv2.LINE_AA)

        if results.pose_landmarks:
            self.drawing_utils.draw_landmarks(image, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS,
                self.drawing_utils.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=2),
                self.drawing_utils.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2))

        return image

# Global state for single camera access
class CameraManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.analyzer = None
        self.analyzer_type = None
        self.frame = None
        self.running = False
        self.thread = None
    
    def start(self, analyzer_cls, analyzer_type):
        with self.lock:
            # If same type, just return
            if self.analyzer_type == analyzer_type and self.running:
                return True
            
            # Stop existing
            self._stop_internal()
            
            # Start new analyzer
            try:
                self.analyzer = analyzer_cls()
                if not self.analyzer.is_opened():
                    self.analyzer = None
                    return False
                self.analyzer_type = analyzer_type
                self.running = True
                self.thread = threading.Thread(target=self._capture_loop, daemon=True)
                self.thread.start()
                return True
            except Exception as e:
                print(f"Failed to start analyzer: {e}")
                return False
    
    def _stop_internal(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None
        if self.analyzer:
            try:
                self.analyzer.release()
            except:
                pass
            self.analyzer = None
        self.frame = None
        self.analyzer_type = None
    
    def _capture_loop(self):
        while self.running and self.analyzer and self.analyzer.is_opened():
            try:
                frame = self.analyzer.read_frame()
                if frame is not None:
                    self.frame = frame.copy()
                else:
                    time.sleep(0.01)
            except Exception as e:
                print(f"Capture error: {e}")
                break
    
    def get_frame(self):
        return self.frame

camera_manager = CameraManager()

HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Fitness Monitor</title>
    <style>
      body {
        font-family: 'Segoe UI', system-ui, sans-serif;
        margin: 0;
        min-height: 100vh;
        background: #0f172a;
        color: #e2e8f0;
        display: flex;
        justify-content: center;
        align-items: center;
      }
      .panel {
        background: #1e293b;
        padding: 2rem;
        border-radius: 18px;
        box-shadow: 0 20px 45px rgba(15, 23, 42, 0.45);
        width: min(980px, 90vw);
      }
      h1 {
        margin: 0 0 0.25rem;
        font-size: 1.8rem;
      }
      .buttons {
        margin-bottom: 1rem;
      }
      button {
        border: none;
        outline: none;
        padding: 0.65rem 1.3rem;
        margin-right: 0.75rem;
        border-radius: 999px;
        font-size: 0.95rem;
        font-weight: 600;
        cursor: pointer;
        transition: transform 0.15s ease, background 0.15s ease;
        background: #4c1d95;
        color: #f8fafc;
      }
      button.active {
        background: #ec4899;
        transform: translateY(-2px);
      }
      img#stream {
        width: 100%;
        border-radius: 12px;
        border: 1px solid #334155;
        background: #020617;
        min-height: 360px;
        max-height: 540px;
        object-fit: contain;
        display: block;
      }
      .loading {
        text-align: center;
        padding: 2rem;
        color: #94a3b8;
      }
      .meta {
        display: flex;
        justify-content: space-between;
        margin-top: 0.75rem;
        font-size: 0.9rem;
        color: #e2e8f0;
      }
    </style>
  </head>
  <body>
    <div class="panel">
      <h1>AI Fitness Monitor</h1>
      <p>Stream live squat or jump feedback from a single camera.</p>
      <div class="buttons">
        <button id="squat" class="active" onclick="activate('squat')">Squat Mode</button>
        <button id="jump" onclick="activate('jump')">Jump Mode</button>
      </div>
      <div id="streamContainer">
        <img id="stream" src="/squat_feed" alt="Live feed" />
      </div>
      <div class="meta">
        <span id="status">Showing squat analysis</span>
        <span>Camera: auto-detected</span>
      </div>
    </div>
    <script>
      const stream = document.getElementById('stream');
      const squatBtn = document.getElementById('squat');
      const jumpBtn = document.getElementById('jump');
      const status = document.getElementById('status');

      function activate(type) {
        // Stop current stream first
        stream.src = '';
        
        if (type === 'squat') {
          stream.src = '/squat_feed?t=' + Date.now();
          squatBtn.classList.add('active');
          jumpBtn.classList.remove('active');
          status.textContent = 'Showing squat analysis';
        } else {
          stream.src = '/jump_feed?t=' + Date.now();
          squatBtn.classList.remove('active');
          jumpBtn.classList.add('active');
          status.textContent = 'Showing jump analysis';
        }
      }

      // Handle image errors
      stream.onerror = function() {
        status.textContent = 'Error loading stream - check camera';
      };
      
      stream.onload = function() {
        console.log('Stream loaded');
      };
    </script>
  </body>
</html>
"""


def _encode_frame(frame) -> bytes:
    ret, buffer = cv2.imencode(".jpg", frame)
    return buffer.tobytes() if ret else b""


def _stream_frames(analyzer_cls, analyzer_type):
    # Start or switch to the requested analyzer type
    if not camera_manager.start(analyzer_cls, analyzer_type):
        # Return a placeholder frame on error
        return
    
    # Stream frames from the camera manager
    while camera_manager.running and camera_manager.analyzer_type == analyzer_type:
        frame = camera_manager.get_frame()
        if frame is not None:
            chunk = _encode_frame(frame)
            if chunk:
                yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + chunk + b"\r\n")
        time.sleep(0.03)  # ~30 FPS


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/squat_feed")
def squat_feed():
    return Response(
        _stream_frames(SquatAnalyzer, "squat"),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/jump_feed")
def jump_feed():
    return Response(
        _stream_frames(JumpAnalyzer, "jump"),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/process_frame", methods=["POST"])
def process_frame():
    """Process a frame from mobile camera and return analyzed frame"""
    try:
        data = request.get_json()
        if not data or "image" not in data:
            return jsonify({"error": "No image data"}), 400
        
        mode = data.get("mode", "squat")
        image_data = data["image"]
        
        # Validate base64 data
        if not image_data or len(image_data) < 100:
            return jsonify({"error": "Invalid image data - too small"}), 400
        
        # Decode base64 image
        try:
            img_bytes = base64.b64decode(image_data)
        except Exception as e:
            return jsonify({"error": f"Base64 decode error: {str(e)}"}), 400
        
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None or frame.size == 0:
            return jsonify({"error": "Failed to decode image"}), 400
        
        # Validate frame dimensions
        if frame.shape[0] < 10 or frame.shape[1] < 10:
            return jsonify({"error": "Image too small"}), 400
        
        # Process frame based on mode
        if mode == "squat":
            analyzer = mobile_processor.get_squat_analyzer()
        else:
            analyzer = mobile_processor.get_jump_analyzer()
        
        processed_frame = analyzer.process_frame(frame)
        
        if processed_frame is None:
            return jsonify({"error": "Processing failed"}), 500
        
        # Encode processed frame to JPEG
        ret, buffer = cv2.imencode(".jpg", processed_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ret:
            return jsonify({"error": "Failed to encode processed frame"}), 500
        
        encoded_image = base64.b64encode(buffer).decode("utf-8")
        
        return jsonify({
            "image": encoded_image,
            "feedback": analyzer.feedback or ""
        })
    except Exception as e:
        print(f"Error processing frame: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/reset_analyzer", methods=["POST"])
def reset_analyzer():
    """Reset analyzer counters"""
    try:
        data = request.get_json()
        mode = data.get("mode", "squat") if data else "squat"
        
        if mode == "squat":
            analyzer = mobile_processor.get_squat_analyzer()
            analyzer.correct_counter = 0
            analyzer.incorrect_counter = 0
            analyzer.sequence = []
            analyzer.stage = None
        else:
            analyzer = mobile_processor.get_jump_analyzer()
            analyzer.jump_count = 0
            analyzer.max_jump_height = 0
            analyzer.baseline_y = None
        
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
