import time
import math
from collections import deque
from cvzone.FaceMeshModule import FaceMeshDetector


class FaceManager:
    def __init__(self, eye_required=1, tilt_required=1, eye_thresh=0.18, tilt_thresh=20, smooth_frames=4, reset_time=1.0, cooldown=2.0):
        # Face detector
        self.detector = FaceMeshDetector(maxFaces=1)

        # Gesture counters
        self.blinks = 0
        self.tilt_left = 0
        self.tilt_right = 0

        # Timing control
        self.last_action = time.time()  # last action timestamp
        self.last_trigger = 0  # last command timestamp

        # Settings
        self.eye_required = eye_required
        self.tilt_required = tilt_required
        self.eye_thresh = eye_thresh
        self.tilt_thresh = tilt_thresh
        self.smooth_frames = smooth_frames
        self.reset_time = reset_time
        self.cooldown = cooldown  # 2 sec cooldown for all commands

        # Smoothing buffers
        self.left_eye_hist = deque(maxlen=smooth_frames)
        self.right_eye_hist = deque(maxlen=smooth_frames)
        self.roll_hist = deque(maxlen=smooth_frames)

    # ----------------------------
    # Process face landmarks and return commands
    # ----------------------------
    def process_face(self, face):
        commands = []
        now = time.time()

        # Reset counters after reset_time
        if now - self.last_action > self.reset_time:
            self.blinks = 0
            self.tilt_left = 0
            self.tilt_right = 0

        # ---- EYE DETECTION → PLAY/PAUSE ----
        left_up, left_down = face[159], face[145]
        left_l, left_r = face[33], face[133]
        right_up, right_down = face[386], face[374]
        right_l, right_r = face[362], face[263]

        left_ratio = abs(left_up[1] - left_down[1]) / \
            abs(left_l[0] - left_r[0])
        right_ratio = abs(right_up[1] - right_down[1]
                          ) / abs(right_l[0] - right_r[0])

        self.left_eye_hist.append(left_ratio)
        self.right_eye_hist.append(right_ratio)

        left_closed = all(r < self.eye_thresh for r in self.left_eye_hist)
        right_closed = all(r < self.eye_thresh for r in self.right_eye_hist)
        both_closed = left_closed and right_closed

        if both_closed and (now - self.last_trigger > self.cooldown):
            self.blinks += 1
            self.last_action = now
            if self.blinks >= self.eye_required:
                commands.append("PLAY_PAUSE")
                self.blinks = 0
                self.last_trigger = now  # update cooldown

        # ---- HEAD TILT → NEXT/PREV TRACK ----
        left_ear, right_ear = face[234], face[454]
        dx, dy = right_ear[0] - left_ear[0], right_ear[1] - left_ear[1]
        roll = math.degrees(math.atan2(dy, dx))
        self.roll_hist.append(roll)
        avg_roll = sum(self.roll_hist) / len(self.roll_hist)

        if avg_roll > self.tilt_thresh and (now - self.last_trigger > self.cooldown):
            self.tilt_right += 1
            self.last_action = now
            if self.tilt_right >= self.tilt_required:
                commands.append("PREV_TRACK")
                self.tilt_right = 0
                self.last_trigger = now

        elif avg_roll < -self.tilt_thresh and (now - self.last_trigger > self.cooldown):
            self.tilt_left += 1
            self.last_action = now
            if self.tilt_left >= self.tilt_required:
                commands.append("NEXT_TRACK")
                self.tilt_left = 0
                self.last_trigger = now

        return commands

    # ----------------------------
    # Detect face from frame and return commands
    # ----------------------------
    def detect_and_process(self, frame):
        frame, faces = self.detector.findFaceMesh(frame, draw=False)
        commands = []
        if faces:
            commands = self.process_face(faces[0])
        return frame, commands
