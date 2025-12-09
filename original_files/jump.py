import math
import os
import time
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np
from dotenv import load_dotenv

load_dotenv()

CALIBRATION_INCHES = float(os.getenv("CALIBRATION_INCHES", "12"))
CALIBRATION_PIXELS = float(os.getenv("CALIBRATION_PIXELS", "100"))
MIN_JUMP_INCHES = float(os.getenv("MIN_JUMP_INCHES", "2.0"))
SMOOTHING_WINDOW = int(os.getenv("SMOOTHING_WINDOW", "5"))
MIN_AIRBORNE_FRAMES = int(os.getenv("MIN_AIRBORNE_FRAMES", "6"))
VEL_UP_PCT_OF_H = float(os.getenv("VEL_UP_PCT_OF_H", "0.25"))
VEL_DOWN_PCT_OF_H = float(os.getenv("VEL_DOWN_PCT_OF_H", "0.25"))

mp_pose = mp.solutions.pose


@dataclass
class JumpResult:
    inches: float
    valid: bool
    reason: str


def inches_per_pixel() -> float:
    return CALIBRATION_INCHES / CALIBRATION_PIXELS if CALIBRATION_PIXELS > 0 else 0.12


def distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def landmark_xy(landmarks, idx, w, h) -> Optional[Tuple[float, float]]:
    lm = landmarks[idx]
    if lm.visibility < 0.4:
        return None
    return (lm.x * w, lm.y * h)


def is_hand_to_nose(
    landmarks,
    w,
    h,
    hand_idx: int,
    nose_idx: int = mp_pose.PoseLandmark.NOSE.value,
    thresh: float = 60.0,
) -> bool:
    p_hand = landmark_xy(landmarks, hand_idx, w, h)
    p_nose = landmark_xy(landmarks, nose_idx, w, h)
    if not p_hand or not p_nose:
        return False
    return distance(p_hand, p_nose) < thresh


def detect_squat_cheat(landmarks, w, h) -> bool:
    idx = mp_pose.PoseLandmark
    pts = {}
    for name in [
        "LEFT_HIP",
        "RIGHT_HIP",
        "LEFT_KNEE",
        "RIGHT_KNEE",
        "LEFT_ANKLE",
        "RIGHT_ANKLE",
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
    def __init__(self, camera_index: int = None):
        # Auto-detect camera if not specified
        if camera_index is None:
            self.cap = None
            for idx in [0, 1, 2]:
                cap = cv2.VideoCapture(idx)
                if cap.isOpened():
                    # Check if camera provides actual non-black frames
                    ret, frame = cap.read()
                    if ret and frame is not None and np.mean(frame) > 10:
                        self.cap = cap
                        print(f"Using camera {idx}")
                        break
                cap.release()
            if self.cap is None:
                # Fallback to camera 1 (often external/USB camera)
                self.cap = cv2.VideoCapture(1)
                if not self.cap.isOpened():
                    self.cap = cv2.VideoCapture(0)
        else:
            self.cap = cv2.VideoCapture(camera_index)
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        try:
            cv2.setUseOptimized(True)
        except Exception:
            pass
        self.pose = mp_pose.Pose(
            model_complexity=0,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.drawing_utils = mp.solutions.drawing_utils
        self.drawing_styles = mp.solutions.drawing_styles
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
        return self.cap.isOpened()

    def release(self) -> None:
        self.cap.release()
        self.pose.close()

    def _reset_state(self) -> None:
        self.state = "idle"
        self.baseline_nose_y = None
        self.peak_delta_pixels = 0.0
        self.prev_dy = None
        self.airborne_frames = 0
        self.nose_history.clear()
        self.steady_frames = 0

    def _finalize_jump(self, landmarks, width: int, height: int) -> None:
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

    def read_frame(self):
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
                    frame,
                    "Armed: ready to measure",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 0),
                    2,
                )

            if self.state in ("armed", "landed") and is_hand_to_nose(
                landmarks, w, h, left_hand_idx, nose_idx
            ):
                self._reset_state()
                self.last_jump_result = None

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
                            frame,
                            "Tap LEFT hand to nose to reset",
                            (10, h - 20),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (0, 255, 255),
                            2,
                        )
                        self.steady_frames = 0
        if results.pose_landmarks:
            self.drawing_utils.draw_landmarks(
                frame,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.drawing_styles.get_default_pose_landmarks_style(),
            )

        if self.last_jump_result:
            text = f"Last: {'VALID' if self.last_jump_result.valid else 'BAD'} {self.last_jump_result.inches:.1f} in ({self.last_jump_result.reason})"
            cv2.putText(
                frame,
                text,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0) if self.last_jump_result.valid else (0, 0, 255),
                2,
            )
        else:
            if self.state == "idle":
                cv2.putText(
                    frame,
                    "Tap RIGHT hand to nose to arm",
                    (10, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (200, 200, 200),
                    1,
                )

        cv2.putText(
            frame,
            f"State: {self.state}",
            (10, h - 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )
        cv2.putText(
            frame,
            "Right hand -> nose: ARM",
            (10, h - 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (200, 200, 200),
            1,
        )
        cv2.putText(
            frame,
            "Left hand -> nose: RESET",
            (10, h - 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (200, 200, 200),
            1,
        )
        cv2.putText(
            frame,
            f"dy(px): {self.dy_debug:.1f}  vel(px/s): {self.vel_debug:.1f}",
            (10, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (180, 200, 255),
            2,
        )

        if dt_local > 0:
            self.fps = 0.9 * self.fps + 0.1 * (1.0 / dt_local)
        self.prev_time = now
        cv2.putText(
            frame,
            f"FPS: {self.fps:.1f}",
            (w - 150, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (100, 255, 100),
            2,
        )

        return frame


def main():
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
