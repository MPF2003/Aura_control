import cv2


class WebcamManager:
    def __init__(self, camera_index=0, width=640, height=480):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.cap = None

    def start(self):
        """Start the webcam."""
        self.cap = cv2.VideoCapture(self.camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open webcam {self.camera_index}")
        print(f"Webcam {self.camera_index} started.")

    def get_frame(self):
        """Capture a single frame from the webcam."""
        if self.cap is None:
            raise RuntimeError("Webcam not started. Call start() first.")
        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError("Failed to read frame from webcam.")
        return frame

    def release(self):
        """Release the webcam."""
        if self.cap:
            self.cap.release()
            cv2.destroyAllWindows()
            print(f"Webcam {self.camera_index} released.")


# Optional test block
if __name__ == "__main__":
    cam = WebcamManager()
    cam.start()
    try:
        while True:
            frame = cam.get_frame()
            cv2.imshow("Webcam", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cam.release()
