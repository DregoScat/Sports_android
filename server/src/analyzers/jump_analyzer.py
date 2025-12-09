"""
Jump Analyzer Module
====================

Real-time vertical jump measurement using MediaPipe pose detection.

Classes:
    JumpAnalyzer: Camera-based jump analyzer with gesture controls
    JumpAnalyzerMobile: Mobile frame processor for jump analysis

Usage:
    # With camera
    analyzer = JumpAnalyzer()
    while analyzer.is_opened():
        frame = analyzer.read_frame()
        
    # Mobile (process individual frames)
    analyzer = JumpAnalyzerMobile()
    processed = analyzer.process_frame(frame)
"""

import math
import os
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np
from dotenv import load_dotenv

# Load environment configuration
load_dotenv()

# Configuration from environment
CALIBRATION_INCHES = float(os.getenv("CALIBRATION_INCHES", "12"))
CALIBRATION_PIXELS = float(os.getenv("CALIBRATION_PIXELS", "100"))
MIN_JUMP_INCHES = float(os.getenv("MIN_JUMP_INCHES", "2.0"))
SMOOTHING_WINDOW = int(os.getenv("SMOOTHING_WINDOW", "5"))
MIN_AIRBORNE_FRAMES = int(os.getenv("MIN_AIRBORNE_FRAMES", "6"))
VEL_UP_PCT_OF_H = float(os.getenv("VEL_UP_PCT_OF_H", "0.25"))
VEL_DOWN_PCT_OF_H = float(os.getenv("VEL_DOWN_PCT_OF_H", "0.25"))

# MediaPipe pose reference
mp_pose = mp.solutions.pose


@dataclass
class JumpResult:
    """Result of a jump measurement."""
    inches: float
    valid: bool
    reason: str


def inches_per_pixel() -> float:
    """Calculate inches per pixel based on calibration settings."""
    return CALIBRATION_INCHES / CALIBRATION_PIXELS if CALIBRATION_PIXELS > 0 else 0.12


def distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calculate Euclidean distance between two points."""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def landmark_xy(landmarks, idx: int, w: int, h: int) -> Optional[Tuple[float, float]]:
    """
    Get landmark coordinates in pixel space.
    
    Args:
        landmarks: MediaPipe landmark list
        idx: Landmark index
        w: Frame width
        h: Frame height
        
    Returns:
        Tuple of (x, y) coordinates or None if visibility is too low
    """
    lm = landmarks[idx]
    if lm.visibility < 0.4:
        return None
    return (lm.x * w, lm.y * h)


def is_hand_to_nose(
    landmarks,
    w: int,
    h: int,
    hand_idx: int,
    nose_idx: int = mp_pose.PoseLandmark.NOSE.value,
    thresh: float = 60.0,
) -> bool:
    """
    Check if hand is near nose (gesture detection).
    
    Args:
        landmarks: MediaPipe landmark list
        w: Frame width
        h: Frame height
        hand_idx: Hand landmark index
        nose_idx: Nose landmark index
        thresh: Distance threshold in pixels
        
    Returns:
        True if hand is within threshold of nose
    """
    p_hand = landmark_xy(landmarks, hand_idx, w, h)
    p_nose = landmark_xy(landmarks, nose_idx, w, h)
    if not p_hand or not p_nose:
        return False
    return distance(p_hand, p_nose) < thresh


def detect_squat_cheat(landmarks, w: int, h: int) -> bool:
    """
    Detect if user is cheating by squatting instead of jumping.
    
    Args:
        landmarks: MediaPipe landmark list
        w: Frame width
        h: Frame height
        
    Returns:
        True if squat cheat is detected
    """
    idx = mp_pose.PoseLandmark
    pts = {}
    for name in [
        "LEFT_HIP", "RIGHT_HIP",
        "LEFT_KNEE", "RIGHT_KNEE",
        "LEFT_ANKLE", "RIGHT_ANKLE",
    ]:
        val = getattr(idx, name).value
        p = landmark_xy(landmarks, val, w, h)
        if not p:
            return False
        pts[name] = p

    hip_y = (pts["LEFT_HIP"][1] + pts["RIGHT_HIP"][1]) / 2
    knee_y = (pts["LEFT_KNEE"][1] + pts["RIGHT_KNEE"][1]) / 2

    def angle(a, b, c):
        ba = np.array(a) - np.array(b)
        bc = np.array(c) - np.array(b)
        cosang = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
        return math.degrees(math.acos(max(min(cosang, 1), -1)))

    knee_angle_left = angle(pts["LEFT_HIP"], pts["LEFT_KNEE"], pts["LEFT_ANKLE"])
    knee_angle_right = angle(pts["RIGHT_HIP"], pts["RIGHT_KNEE"], pts["RIGHT_ANKLE"])
    knee_angle = (knee_angle_left + knee_angle_right) / 2

    is_knee_bent = knee_angle < 150
    is_hip_low = hip_y > (knee_y - 20)
    is_ankle_under = (
        abs(
            (pts["LEFT_ANKLE"][0] + pts["RIGHT_ANKLE"][0]) / 2
            - (pts["LEFT_HIP"][0] + pts["RIGHT_HIP"][0]) / 2
        )
        < 60
    )

    return is_knee_bent and (is_hip_low or is_ankle_under)


class JumpAnalyzer:
    """
    Jump analyzer with camera capture and gesture controls.
    
    Gestures:
        - Right hand to nose: ARM the system
        - Left hand to nose: RESET the measurement
    
    Attributes:
        state (str): Current state (idle, armed, airborne, landed)
        last_jump_result (JumpResult): Result of the last completed jump
    """
    
    def __init__(self, camera_index: Optional[int] = None):
        """
        Initialize the jump analyzer.
        
        Args:
            camera_index: Specific camera index to use, or None for auto-detect
        """
        self._init_camera(camera_index)
        self._init_pose_detection()
        self._init_state()

    def _init_camera(self, camera_index: Optional[int]) -> None:
        """Initialize camera with auto-detection if needed."""
        if camera_index is None:
            self.cap = self._auto_detect_camera()
        else:
            self.cap = cv2.VideoCapture(camera_index)
        
        # Configure camera
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        try:
            cv2.setUseOptimized(True)
        except Exception:
            pass
    
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
        self.pose = mp_pose.Pose(
            model_complexity=0,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.drawing_utils = mp.solutions.drawing_utils
        self.drawing_styles = mp.solutions.drawing_styles
    
    def _init_state(self) -> None:
        """Initialize state tracking variables."""
        self.state = "idle"
        self.baseline_nose_y = None
        self.peak_delta_pixels = 0.0
        self.last_land_time = 0.0
        self.last_jump_result: Optional[JumpResult] = None
        self.prev_dy: Optional[float] = None
        self.airborne_frames = 0
        self.prev_time = time.time()
        self.fps = 0.0
        self.dy_debug = 0.0
        self.vel_debug = 0.0
        self.nose_history = []
        self.steady_frames = 0
        self.min_airborne_frames = MIN_AIRBORNE_FRAMES

    def is_opened(self) -> bool:
        """Check if camera is opened and ready."""
        return self.cap.isOpened()

    def release(self) -> None:
        """Release camera and cleanup resources."""
        self.cap.release()
        self.pose.close()

    def _reset_state(self) -> None:
        """Reset jump detection state."""
        self.state = "idle"
        self.baseline_nose_y = None
        self.peak_delta_pixels = 0.0
        self.prev_dy = None
        self.airborne_frames = 0
        self.nose_history.clear()
        self.steady_frames = 0

    def _finalize_jump(self, landmarks, width: int, height: int) -> None:
        """Finalize and validate jump measurement."""
        inches = max(0.0, self.peak_delta_pixels) * inches_per_pixel()
        if inches < MIN_JUMP_INCHES:
            self.last_jump_result = JumpResult(
                inches=inches, valid=False, reason="too-small"
            )
        else:
            cheated = detect_squat_cheat(landmarks, width, height)
            if cheated:
                self.last_jump_result = JumpResult(
                    inches=inches, valid=False, reason="cheat"
                )
            else:
                self.last_jump_result = JumpResult(
                    inches=inches, valid=True, reason="ok"
                )

    def read_frame(self) -> Optional[np.ndarray]:
        """
        Read and process a frame from the camera.
        
        Returns:
            Annotated frame with pose overlay and jump data, or None if capture failed
        """
        if not self.cap.isOpened():
            return None
        ret, frame = self.cap.read()
        if not ret:
            return None

        now = time.time()
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)
        landmarks = results.pose_landmarks.landmark if results.pose_landmarks else None
        dt_local = now - self.prev_time if self.prev_time else 0.0

        if landmarks:
            nose_idx = mp_pose.PoseLandmark.NOSE.value
            right_hand_idx = mp_pose.PoseLandmark.RIGHT_INDEX.value
            left_hand_idx = mp_pose.PoseLandmark.LEFT_INDEX.value

            # Check for ARM gesture
            if self.state == "idle" and is_hand_to_nose(
                landmarks, w, h, right_hand_idx, nose_idx
            ):
                self.state = "armed"
                p_nose = landmark_xy(landmarks, nose_idx, w, h)
                if p_nose:
                    self.baseline_nose_y = p_nose[1]
                    self.peak_delta_pixels = 0.0
                self.steady_frames = 0
                cv2.putText(
                    frame, "Armed: ready to measure",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2,
                )

            # Check for RESET gesture
            if self.state in ("armed", "landed") and is_hand_to_nose(
                landmarks, w, h, left_hand_idx, nose_idx
            ):
                self._reset_state()
                self.last_jump_result = None

            # Process jump detection
            p_nose = landmark_xy(landmarks, nose_idx, w, h)
            if p_nose and self.baseline_nose_y is not None:
                self.nose_history.append(p_nose[1])
                if len(self.nose_history) > max(5, SMOOTHING_WINDOW):
                    self.nose_history.pop(0)
                smooth_nose_y = sum(self.nose_history) / len(self.nose_history)
                
                if abs(smooth_nose_y - self.baseline_nose_y) < 4:
                    self.steady_frames += 1
                else:
                    self.steady_frames = 0
                
                dy = self.baseline_nose_y - smooth_nose_y
                self.dy_debug = dy
                vel_dy = 0.0
                if self.prev_dy is not None and dt_local > 0:
                    vel_dy = (dy - self.prev_dy) / dt_local
                self.vel_debug = vel_dy
                self.prev_dy = dy
                self.peak_delta_pixels = max(self.peak_delta_pixels, dy)
                
                arm_thresh = max(8, 0.015 * h)
                land_thresh = max(5, 0.01 * h)
                up_vel_thresh = VEL_UP_PCT_OF_H * h
                down_vel_thresh = VEL_DOWN_PCT_OF_H * h

                ready_to_jump = self.steady_frames >= 5
                if (
                    self.state == "armed"
                    and ready_to_jump
                    and dy > arm_thresh
                    and vel_dy > up_vel_thresh
                ):
                    self.state = "airborne"
                    self.airborne_frames = 0
                elif self.state == "airborne":
                    self.airborne_frames += 1
                    if (
                        dy < land_thresh
                        and vel_dy < -down_vel_thresh
                        and self.airborne_frames >= self.min_airborne_frames
                    ):
                        self.state = "landed"
                        self.last_land_time = now
                        self._finalize_jump(landmarks, w, h)
                        cv2.putText(
                            frame, "Tap LEFT hand to nose to reset",
                            (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2,
                        )
                        self.steady_frames = 0

        # Draw pose landmarks
        if results.pose_landmarks:
            self.drawing_utils.draw_landmarks(
                frame,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.drawing_styles.get_default_pose_landmarks_style(),
            )

        # Draw UI overlay
        if self.last_jump_result:
            text = f"Last: {'VALID' if self.last_jump_result.valid else 'BAD'} {self.last_jump_result.inches:.1f} in ({self.last_jump_result.reason})"
            color = (0, 255, 0) if self.last_jump_result.valid else (0, 0, 255)
            cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        else:
            if self.state == "idle":
                cv2.putText(
                    frame, "Tap RIGHT hand to nose to arm",
                    (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1,
                )

        cv2.putText(frame, f"State: {self.state}", (10, h - 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, "Right hand -> nose: ARM", (10, h - 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.putText(frame, "Left hand -> nose: RESET", (10, h - 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.putText(frame, f"dy(px): {self.dy_debug:.1f}  vel(px/s): {self.vel_debug:.1f}",
                    (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 200, 255), 2)

        # FPS counter
        if dt_local > 0:
            self.fps = 0.9 * self.fps + 0.1 * (1.0 / dt_local)
        self.prev_time = now
        cv2.putText(frame, f"FPS: {self.fps:.1f}", (w - 150, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 255, 100), 2)

        return frame


class JumpAnalyzerMobile:
    """
    Jump analyzer for processing mobile camera frames.
    
    This version doesn't use a camera directly - it processes
    individual frames sent from a mobile device.
    """
    
    def __init__(self):
        """Initialize the mobile jump analyzer."""
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose()
        self.drawing_utils = mp.solutions.drawing_utils
        self.baseline_y = None
        self.max_jump_height = 0
        self.jump_count = 0
        self.is_jumping = False
        self.current_jump_height = 0
        self.feedback = None
        self.y_history = deque(maxlen=5)

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Process a single frame and return annotated image.
        
        Args:
            frame: BGR image from mobile camera
            
        Returns:
            Annotated BGR image with pose overlay and jump data
        """
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
                
                if jump_pixels > 30:
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

    def reset(self) -> None:
        """Reset all counters and state."""
        self.jump_count = 0
        self.max_jump_height = 0
        self.baseline_y = None
        self.is_jumping = False
        self.current_jump_height = 0
        self.feedback = None
        self.y_history.clear()


def main():
    """Main entry point for standalone execution."""
    analyzer = JumpAnalyzer()
    if not analyzer.is_opened():
        print("Error: Could not open webcam.")
        return
    while analyzer.is_opened():
        frame = analyzer.read_frame()
        if frame is None:
            break
        cv2.imshow("Vertical Jump Measurement", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == 27 or key == ord("q"):
            break
    analyzer.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
