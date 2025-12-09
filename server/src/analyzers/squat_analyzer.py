"""
Squat Analyzer Module
=====================

Real-time squat form analysis using MediaPipe pose detection.

Classes:
    SquatAnalyzer: Camera-based squat analyzer with audio feedback
    SquatAnalyzerMobile: Mobile frame processor for squat analysis

Usage:
    # With camera
    analyzer = SquatAnalyzer()
    while analyzer.is_opened():
        frame = analyzer.read_frame()
        
    # Mobile (process individual frames)
    analyzer = SquatAnalyzerMobile()
    processed = analyzer.process_frame(frame)
"""

import queue
import threading
from collections import deque
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np
import pyttsx3


class SquatAnalyzer:
    """
    Squat analyzer with camera capture and audio feedback.
    
    Attributes:
        correct_counter (int): Number of correct squats detected
        incorrect_counter (int): Number of incorrect squats detected
        stage (str): Current squat stage (S1, S2, S3, or None)
        feedback (str): Current feedback message
    """
    
    # Squat stage thresholds (knee angles in degrees)
    STAGE_S1_THRESHOLD = 160  # Standing position
    STAGE_S2_THRESHOLD = 95   # Partial squat
    
    # Visibility threshold for landmarks
    VISIBILITY_THRESHOLD = 0.8
    
    # Depth hold requirement (frames at S3)
    DEPTH_HOLD_REQUIREMENT = 3
    
    def __init__(self, camera_index: Optional[int] = None):
        """
        Initialize the squat analyzer.
        
        Args:
            camera_index: Specific camera index to use, or None for auto-detect
        """
        self._init_camera(camera_index)
        self._init_pose_detection()
        self._init_counters()
        self._init_speech()

    def _init_camera(self, camera_index: Optional[int]) -> None:
        """Initialize camera with auto-detection if needed."""
        if camera_index is None:
            self.cap = self._auto_detect_camera()
        else:
            self.cap = cv2.VideoCapture(camera_index)
    
    def _auto_detect_camera(self) -> cv2.VideoCapture:
        """Auto-detect a working camera that provides non-black frames."""
        for idx in [0, 1, 2]:
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None and np.mean(frame) > 10:
                    print(f"Using camera {idx}")
                    return cap
            cap.release()
        
        # Fallback
        cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)
        return cap
    
    def _init_pose_detection(self) -> None:
        """Initialize MediaPipe pose detection."""
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose()
        self.drawing_utils = mp.solutions.drawing_utils
    
    def _init_counters(self) -> None:
        """Initialize counters and state tracking."""
        self.correct_counter = 0
        self.incorrect_counter = 0
        self.stage = None
        self.sequence = []
        self.last_feedback = None
        self.feedback = None
        self.knee_history = deque(maxlen=5)
        self.back_history = deque(maxlen=5)
        self.depth_hold = 0
        self.min_knee_angle = 180
    
    def _init_speech(self) -> None:
        """Initialize text-to-speech in a worker thread."""
        self.engine = None
        self.speech_queue: "queue.Queue[str]" = queue.Queue()
        self._stop_speech = False
        self.speech_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self.speech_thread.start()

    def is_opened(self) -> bool:
        """Check if camera is opened and ready."""
        return self.cap.isOpened()

    def release(self) -> None:
        """Release camera and cleanup resources."""
        self.cap.release()
        self.pose.close()
        self._stop_speech = True
        self.speech_queue.put(None)
        self.speech_thread.join(timeout=2.0)

    def _speak(self, text: str) -> None:
        """Queue text for speech output."""
        if text and text != self.last_feedback:
            self.last_feedback = text
            self.speech_queue.put(text)

    def _speech_worker(self) -> None:
        """Worker thread for text-to-speech."""
        try:
            engine = pyttsx3.init()
        except Exception:
            engine = None
        
        while not self._stop_speech:
            try:
                payload = self.speech_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if payload is None:
                break
            if engine:
                try:
                    engine.say(payload)
                    engine.runAndWait()
                except Exception:
                    pass
        
        if engine:
            try:
                engine.stop()
            except Exception:
                pass

    @staticmethod
    def _calculate_angle(a, b, c) -> float:
        """
        Calculate angle between three points.
        
        Args:
            a: First point [x, y]
            b: Middle point (vertex) [x, y]
            c: Third point [x, y]
            
        Returns:
            Angle in degrees
        """
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

    def _get_landmark(self, landmarks, name: str) -> list:
        """Get landmark coordinates and visibility."""
        lm = landmarks[self.mp_pose.PoseLandmark[name].value]
        return [lm.x, lm.y, lm.visibility]

    def _draw_overlay(self, image: np.ndarray) -> None:
        """Draw UI overlay with counters and feedback."""
        frame_h, frame_w = image.shape[:2]
        
        # Header bar
        cv2.rectangle(image, (0, 0), (350, 73), (245, 117, 16), -1)
        
        # Counter labels
        cv2.putText(image, "CORRECT", (15, 12), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(image, str(self.correct_counter), (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 2, cv2.LINE_AA)
        
        cv2.putText(image, "INCORRECT", (120, 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(image, str(self.incorrect_counter), (125, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 2, cv2.LINE_AA)
        
        cv2.putText(image, "STAGE", (250, 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        stage_text = self.stage if self.stage else "N/A"
        cv2.putText(image, stage_text, (245, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 2, cv2.LINE_AA)
        
        # Feedback bar
        if self.feedback:
            cv2.rectangle(image, (0, frame_h - 60), (frame_w, frame_h), (0, 0, 0), -1)
            cv2.putText(image, self.feedback, (20, frame_h - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 2, cv2.LINE_AA)

    def read_frame(self) -> Optional[np.ndarray]:
        """
        Read and process a frame from the camera.
        
        Returns:
            Annotated frame with pose overlay, or None if capture failed
        """
        ret, frame = self.cap.read()
        if not ret:
            return None

        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = self.pose.process(image)
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        feedback = None

        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            shoulder = self._get_landmark(landmarks, "LEFT_SHOULDER")
            hip = self._get_landmark(landmarks, "LEFT_HIP")
            knee = self._get_landmark(landmarks, "LEFT_KNEE")
            ankle = self._get_landmark(landmarks, "LEFT_ANKLE")

            if all(lm[2] > self.VISIBILITY_THRESHOLD for lm in [shoulder, hip, knee, ankle]):
                # Calculate angles
                knee_angle = self._calculate_angle(hip, knee, ankle)
                back_angle = self._calculate_angle(shoulder, hip, knee)
                
                # Smooth angles
                self.knee_history.append(knee_angle)
                self.back_history.append(back_angle)
                knee_angle = sum(self.knee_history) / len(self.knee_history)
                back_angle = sum(self.back_history) / len(self.back_history)
                self.min_knee_angle = min(self.min_knee_angle, knee_angle)

                # Draw angle text
                frame_h, frame_w = image.shape[:2]
                cv2.putText(image, f"Knee: {int(knee_angle)}",
                    tuple(np.multiply(knee[:2], [frame_w, frame_h]).astype(int)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.putText(image, f"Back: {int(back_angle)}",
                    tuple(np.multiply(hip[:2], [frame_w, frame_h]).astype(int)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)

                # Determine stage
                prev_stage = self.stage
                if knee_angle > self.STAGE_S1_THRESHOLD:
                    self.stage = "S1"
                elif self.STAGE_S1_THRESHOLD >= knee_angle > self.STAGE_S2_THRESHOLD:
                    self.stage = "S2"
                elif knee_angle <= self.STAGE_S2_THRESHOLD:
                    self.stage = "S3"

                if self.stage and prev_stage != self.stage:
                    self.sequence.append(self.stage)

                # Track depth hold - only increment in S3
                if self.stage == "S3":
                    self.depth_hold += 1
                # Don't reset depth_hold here - keep it for squat validation

                # Check for squat completion - must have gone through full cycle
                if (len(self.sequence) >= 3 
                    and self.sequence[-3:] == ["S2", "S3", "S2"]
                    and self.depth_hold >= self.DEPTH_HOLD_REQUIREMENT):
                    self.correct_counter += 1
                    feedback = "Correct Squat"
                    self.sequence = []
                    self.min_knee_angle = 180
                    self.depth_hold = 0
                elif (len(self.sequence) >= 4 
                    and "S3" in self.sequence 
                    and self.sequence[-1] == "S1"
                    and self.depth_hold >= self.DEPTH_HOLD_REQUIREMENT):
                    # S1->S2->S3->S2->S1 pattern (full squat cycle)
                    self.correct_counter += 1
                    feedback = "Correct Squat"
                    self.sequence = []
                    self.min_knee_angle = 180
                    self.depth_hold = 0
                elif len(self.sequence) >= 3 and self.sequence[-1] == "S1":
                    if self.sequence != ["S1"] and "S3" not in self.sequence:
                        self.incorrect_counter += 1
                        feedback = "Incomplete - Go deeper"
                    elif self.sequence != ["S1"] and self.depth_hold < self.DEPTH_HOLD_REQUIREMENT:
                        self.incorrect_counter += 1
                        feedback = "Hold at bottom longer"
                    self.sequence = []
                    self.depth_hold = 0

                # Form feedback
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
                self._speak(feedback)
            else:
                feedback = "Please make your full body visible"
                self.feedback = feedback
                self._speak(feedback)
        else:
            feedback = "Please make your full body visible"
            self.feedback = feedback
            self._speak(feedback)

        # Draw overlays
        self._draw_overlay(image)
        
        if results.pose_landmarks:
            self.drawing_utils.draw_landmarks(
                image,
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                self.drawing_utils.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=2),
                self.drawing_utils.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2),
            )

        return image


class SquatAnalyzerMobile:
    """
    Squat analyzer for processing mobile camera frames.
    
    This version doesn't use a camera directly - it processes
    individual frames sent from a mobile device.
    """
    
    STAGE_S1_THRESHOLD = 160
    STAGE_S2_THRESHOLD = 95
    VISIBILITY_THRESHOLD = 0.8
    DEPTH_HOLD_REQUIREMENT = 3
    
    def __init__(self):
        """Initialize the mobile squat analyzer."""
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose()
        self.drawing_utils = mp.solutions.drawing_utils
        self.correct_counter = 0
        self.incorrect_counter = 0
        self.stage = None
        self.sequence = []
        self.feedback = None
        self.knee_history = deque(maxlen=5)
        self.back_history = deque(maxlen=5)
        self.depth_hold = 0
        self.min_knee_angle = 180

    @staticmethod
    def _calculate_angle(a, b, c) -> float:
        """Calculate angle between three points."""
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

    def _get_landmark(self, landmarks, name: str) -> list:
        """Get landmark coordinates and visibility."""
        lm = landmarks[self.mp_pose.PoseLandmark[name].value]
        return [lm.x, lm.y, lm.visibility]

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Process a single frame and return annotated image.
        
        Args:
            frame: BGR image from mobile camera
            
        Returns:
            Annotated BGR image with pose overlay and feedback
        """
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

            if all(lm[2] > self.VISIBILITY_THRESHOLD for lm in [shoulder, hip, knee, ankle]):
                knee_angle = self._calculate_angle(hip, knee, ankle)
                back_angle = self._calculate_angle(shoulder, hip, knee)
                self.knee_history.append(knee_angle)
                self.back_history.append(back_angle)
                knee_angle = sum(self.knee_history) / len(self.knee_history)
                back_angle = sum(self.back_history) / len(self.back_history)
                self.min_knee_angle = min(self.min_knee_angle, knee_angle)

                frame_h, frame_w = image.shape[:2]
                cv2.putText(image, f"Knee: {int(knee_angle)}",
                    tuple(np.multiply(knee[:2], [frame_w, frame_h]).astype(int)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.putText(image, f"Back: {int(back_angle)}",
                    tuple(np.multiply(hip[:2], [frame_w, frame_h]).astype(int)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)

                prev_stage = self.stage
                if knee_angle > self.STAGE_S1_THRESHOLD:
                    self.stage = "S1"
                elif self.STAGE_S1_THRESHOLD >= knee_angle > self.STAGE_S2_THRESHOLD:
                    self.stage = "S2"
                elif knee_angle <= self.STAGE_S2_THRESHOLD:
                    self.stage = "S3"

                if self.stage and prev_stage != self.stage:
                    self.sequence.append(self.stage)

                # Track depth hold - only increment in S3, reset otherwise
                if self.stage == "S3":
                    self.depth_hold += 1
                elif prev_stage == "S3" and self.stage != "S3":
                    # Transitioning out of S3 - don't reset yet, keep for validation
                    pass

                feedback = None
                # Check for correct squat - S1->S2->S3->S2->S1 or S2->S3->S2
                if len(self.sequence) >= 3 and self.sequence[-3:] == ["S1", "S2", "S3"] and self.depth_hold >= 3:
                    if knee_angle > 100:
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
                    elif self.sequence != ["S1"] and self.depth_hold < 3:
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

    def reset(self) -> None:
        """Reset all counters and state."""
        self.correct_counter = 0
        self.incorrect_counter = 0
        self.sequence = []
        self.stage = None
        self.depth_hold = 0
        self.min_knee_angle = 180
        self.feedback = None
        self.knee_history.clear()
        self.back_history.clear()


if __name__ == "__main__":
    # Standalone execution for testing
    analyzer = SquatAnalyzer()
    while analyzer.is_opened():
        frame = analyzer.read_frame()
        if frame is None:
            break
        cv2.imshow("AI Fitness Trainer - Squat Analysis", frame)
        if cv2.waitKey(10) & 0xFF == ord("q"):
            break
    analyzer.release()
    cv2.destroyAllWindows()
