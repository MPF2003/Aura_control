from cvzone.HandTrackingModule import HandDetector
import time


class HandManager:
    def __init__(self, detectionCon=0.8, maxHands=2, volume_cooldown=0.3, toggle_cooldown=7):
        """
        HandManager detects hand gestures:
        - Thumbs up/down → volume control
        - Open hand → mute/unmute toggle
        """
        self.detector = HandDetector(
            detectionCon=detectionCon, maxHands=maxHands)
        self.volume_cooldown = volume_cooldown
        self.toggle_cooldown = toggle_cooldown
        self.last_volume_time = 0
        self.last_toggle_time = 0
        self.is_muted = False  # current mute/unmute state

    def detect_hands(self, frame):
        """
        Detect hands in a frame.
        Returns: hands list, annotated frame
        """
        hands, img = self.detector.findHands(frame)
        return hands, img

    def gesture_volume_and_toggle(self, hand):
        """
        Detect gestures for volume and mute/unmute.
        - Thumbs (single finger) → volume
        - Open hand (all fingers) → mute/unmute toggle
        """
        fingers = self.detector.fingersUp(hand)
        hand_type = hand['type']
        now = time.time()

        # ------------------------
        # MUTE/UNMUTE toggle
        # ------------------------
        if fingers == [1, 1, 1, 1, 1] and now - self.last_toggle_time > self.toggle_cooldown:
            self.last_toggle_time = now
            self.is_muted = not self.is_muted
            return 'MUTE' if self.is_muted else 'UNMUTE'

        # ------------------------
        # VOLUME control (thumb gestures)
        # ------------------------
        if now - self.last_volume_time < self.volume_cooldown:
            return None

        action = None
        if hand_type == 'Right':
            if fingers == [1, 0, 0, 0, 0]:
                action = 'VOLUME_DOWN'
            elif fingers == [0, 0, 0, 0, 0]:
                action = 'VOLUME_UP'
        elif hand_type == 'Left':
            if fingers == [1, 0, 0, 0, 0]:
                action = 'VOLUME_UP'
            elif fingers == [0, 0, 0, 0, 0]:
                action = 'VOLUME_DOWN'

        if action:
            self.last_volume_time = now
            return action

        return None
