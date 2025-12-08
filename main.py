import time
from webcam_manager import WebcamManager
from face import FaceManager
from hand import HandManager
from spotify_player import SpotifyPlayer

# Initialize modules
cam = WebcamManager()
cam.start()

face_manager = FaceManager()
hand_manager = HandManager(maxHands=2)

# Replace with your Spotify credentials
spotify = SpotifyPlayer(
    client_id="ba3712c147094d3e8291abe866ceae2b",
    client_secret="9f2c96ee53c6439da9b4b7491cd4c84d",
    redirect_uri="http://127.0.0.1:8888/callback"
)

# Command cooldowns

last_hand_time = 0
hand_interval = 0.3
last_mute_time = 0
mute_interval = 2
volume_step = 10
last_volume = None

# Helper: adjust Spotify volume


def change_spotify_volume(direction):
    device = spotify.ensure_device()
    if not device:
        print("No active device for volume control")
        return

    try:
        current = spotify.sp.current_playback()
        if not current or not current['device']:
            print("Cannot read current volume")
            return

        vol = current['device']['volume_percent']
        if direction == "UP":
            vol = min(vol + volume_step, 100)
        elif direction == "DOWN":
            vol = max(vol - volume_step, 0)

        spotify.sp.volume(vol, device_id=device)
        print(f"Volume set to {vol}%")
    except Exception as e:
        print("Error changing volume:", e)


# Main loop
try:
    while True:
        frame = cam.get_frame()
        if frame is None:
            print("Failed to read frame, skipping iteration")
            time.sleep(0.1)
            continue

        now = time.time()

        # ---- Face gestures (cooldown in FaceManager) ----
        frame, face_cmds = face_manager.detect_and_process(frame)
        for cmd in face_cmds:
            print(f"Face command: {cmd}")

            if cmd == "PLAY_PAUSE":
                try:
                    # Read playback state ONCE
                    playback = spotify.sp.current_playback()
                    is_playing = playback['is_playing'] if playback else False
                    print(
                        f"Face command: PLAY_PAUSE | is_playing: {is_playing}")

                    # Use FIXED pause/resume methods
                    if is_playing:
                        spotify.pause()   # ← Uses active device
                        print("Paused")
                    else:
                        spotify.resume()  # ← Uses active device
                        print("Resumed")

                except Exception as e:
                    print("Playback toggle failed:", e)

            elif cmd == "NEXT_TRACK":
                try:
                    spotify.next()  # ← Use wrapper
                    print("Next track")
                except Exception as e:
                    print("Next track failed:", e)

            elif cmd == "PREV_TRACK":
                try:
                    spotify.previous()  # ← Use wrapper
                    print("Previous track")
                except Exception as e:
                    print("Previous track failed:", e)

        # ---- Hand gestures ----
        hands, annotated = hand_manager.detect_hands(frame)

        for hand in hands:
            gesture = hand_manager.gesture_volume_and_toggle(hand)

            # Volume control
            if gesture in ["VOLUME_UP", "VOLUME_DOWN"] and now - last_hand_time > hand_interval:
                change_spotify_volume(
                    "UP" if gesture == "VOLUME_UP" else "DOWN")
                last_hand_time = now

            # Mute/unmute
            if gesture in ["MUTE", "UNMUTE"] and now - last_mute_time > mute_interval:
                device = spotify.ensure_device()
                if not device:
                    continue

                current = spotify.sp.current_playback()
                current_vol = current['device']['volume_percent'] if current and current['device'] else 50

                if gesture == "MUTE":
                    last_volume = current_vol
                    spotify.sp.volume(0, device_id=device)
                    print("Muted to volume set to 0")
                elif gesture == "UNMUTE":
                    restore_vol = last_volume if last_volume is not None else 50
                    spotify.sp.volume(restore_vol, device_id=device)
                    print(f"Unmuted to volume restored to {restore_vol}%")

                last_mute_time = now

finally:
    cam.release()
