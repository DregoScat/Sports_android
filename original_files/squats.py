import threading
import queue
from collections import deque

import cv2
import mediapipe as mp
import numpy as np
import pyttsx3


class SquatAnalyzer:
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
        
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose()
        self.drawing_utils = mp.solutions.drawing_utils
        self.correct_counter = 0
        self.incorrect_counter = 0
        self.stage = None
        self.sequence = []
        self.last_feedback = None
        self.feedback = None
        # Don't initialize pyttsx3 here - it must be in the same thread as runAndWait()
        self.engine = None
        self.knee_history = deque(maxlen=5)
        self.back_history = deque(maxlen=5)
        self.depth_hold = 0
        self.min_knee_angle = 180
        self.speech_queue: "queue.Queue[str]" = queue.Queue()
        self._stop_speech = False
        self.speech_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self.speech_thread.start()

    def is_opened(self) -> bool:
        return self.cap.isOpened()

    def release(self) -> None:
        self.cap.release()
        self.pose.close()
        self._stop_speech = True
        self.speech_queue.put(None)
        self.speech_thread.join(timeout=2.0)  # Don't block forever

    def _speak(self, text: str) -> None:
        if text and text != self.last_feedback:
            self.last_feedback = text
            self.speech_queue.put(text)

    def _speech_worker(self) -> None:
        # Initialize pyttsx3 in the worker thread - required for proper functioning
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
                    pass  # Ignore speech errors to keep the app running
        
        if engine:
            try:
                engine.stop()
            except Exception:
                pass

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

    def read_frame(self):
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

                # Get actual frame dimensions for proper text positioning
                frame_h, frame_w = image.shape[:2]
                cv2.putText(
                    image,
                    f"Knee: {int(knee_angle)}",
                    tuple(np.multiply(knee[:2], [frame_w, frame_h]).astype(int)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    image,
                    f"Back: {int(back_angle)}",
                    tuple(np.multiply(hip[:2], [frame_w, frame_h]).astype(int)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )

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
                else:
                    self.depth_hold = 0

                if (
                    len(self.sequence) >= 3
                    and self.sequence[-3:] == ["S2", "S3", "S2"]
                    and self.depth_hold >= 3
                ):
                    self.correct_counter += 1
                    feedback = "Correct Squat"
                    self.sequence = []
                    self.min_knee_angle = 180
                    self.depth_hold = 0
                elif len(self.sequence) >= 3 and self.sequence[-1] == "S1":
                    if self.sequence != ["S1"]:
                        self.incorrect_counter += 1
                        feedback = "Incorrect Squat"
                    self.sequence = []

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

        cv2.rectangle(image, (0, 0), (350, 73), (245, 117, 16), -1)
        cv2.putText(
            image,
            "CORRECT",
            (15, 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 0),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            image,
            str(self.correct_counter),
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            2,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            image,
            "INCORRECT",
            (120, 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 0),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            image,
            str(self.incorrect_counter),
            (125, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            2,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            image,
            "STAGE",
            (250, 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 0),
            1,
            cv2.LINE_AA,
        )
        stage_text = self.stage if self.stage else "N/A"
        cv2.putText(
            image,
            stage_text,
            (245, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            2,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        # Display feedback text at the bottom of the screen
        if self.feedback:
            frame_h, frame_w = image.shape[:2]
            # Background rectangle for feedback
            cv2.rectangle(image, (0, frame_h - 60), (frame_w, frame_h), (0, 0, 0), -1)
            # Feedback text
            cv2.putText(
                image,
                self.feedback,
                (20, frame_h - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2,
                (0, 255, 255),  # Yellow color for visibility
                2,
                cv2.LINE_AA,
            )

        if results.pose_landmarks:
            self.drawing_utils.draw_landmarks(
                image,
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                self.drawing_utils.DrawingSpec(
                    color=(245, 117, 66), thickness=2, circle_radius=2
                ),
                self.drawing_utils.DrawingSpec(
                    color=(245, 66, 230), thickness=2, circle_radius=2
                ),
            )

        return image


if __name__ == "__main__":
    analyzer = SquatAnalyzer()
    while analyzer.is_opened():
        frame = analyzer.read_frame()
        if frame is None:
            break
        cv2.imshow("AI Fitness Trainer", frame)
        if cv2.waitKey(10) & 0xFF == ord("q"):
            break
    analyzer.release()
    cv2.destroyAllWindows()
