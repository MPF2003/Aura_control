import spotipy
from spotipy.oauth2 import SpotifyOAuth
import random


class SpotifyPlayer:

    EMOTION_GENRES = {
        "happy": ["pop", "dance", "latin"],
        "sad": ["acoustic", "classical", "blues"],
        "angry": ["rock", "metal", "punk"],
        "surprise": ["electronic", "house", "edm"],
        "disgust": ["soul", "r&b", "blues"],
        "fear": ["ambient", "soundtracks", "darkwave"],
        "neutral": ["indie", "chill", "lofi"]
    }

    EMOTION_TARGETS = {
        "happy":     {"valence": (0.7, 1.0), "energy": (0.6, 1.0), "danceability": (0.5, 1.0)},
        "sad":       {"valence": (0.0, 0.3), "energy": (0.0, 0.3), "acousticness": (0.4, 1.0)},
        "angry":     {"valence": (0.1, 0.4), "energy": (0.6, 1.0), "tempo": (90, 150)},
        "surprise":  {"valence": (0.5, 0.8), "energy": (0.6, 0.9), "danceability": (0.5, 0.8)},
        "disgust":   {"valence": (0.2, 0.5), "energy": (0.3, 0.6), "acousticness": (0.4, 0.7)},
        "fear":      {"valence": (0.0, 0.4), "energy": (0.2, 0.5), "instrumentalness": (0.3, 1.0)},
        "neutral":   {"valence": (0.4, 0.6), "energy": (0.4, 0.6)}
    }

    def __init__(self, client_id, client_secret, redirect_uri):
        scope = (
            "user-read-playback-state user-modify-playback-state "
            "user-read-currently-playing playlist-read-private "
            "user-top-read streaming"
        )
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope,
            cache_path=".spotify_cache",
            open_browser=True
        ))
        print("SpotifyPlayer → Aura Control Loaded")

    # -------------------------------
    # DEVICE HANDLING
    # -------------------------------
    def get_active_device(self):
        try:
            devices = self.sp.devices().get("devices", [])
            if not devices:
                return None
            active = next((d for d in devices if d["is_active"]), None)
            return active["id"] if active else devices[0]["id"]
        except:
            return None

    def ensure_device(self):
        device = self.get_active_device()
        if device:
            try:
                self.sp.transfer_playback(device)
            except:
                pass
        return device

    # -------------------------------
    # PLAYBACK FOR EMOTION
    # -------------------------------
    def play_for_emotion(self, emotion: str):
        emotion = emotion.lower()
        device = self.ensure_device()
        if not device:
            print("No active Spotify device found.")
            return False

        queue = (
            self._layer_user_recommendations(emotion)
            or self._layer_playlist_matches(emotion)
            or self._layer_global_recommendations(emotion)
        )

        if not queue:
            print("No tracks found for emotion.")
            return False

        try:
            self.sp.start_playback(device_id=device, uris=queue[:50])
            print(f"▶ NOW PLAYING ({emotion.upper()}) — {len(queue)} tracks")
            return True
        except Exception as e:
            print("Playback failed:", e)
            return False

    # -------------------------------
    # LAYER 1 — USER-BASED RECOMMENDATIONS
    # -------------------------------
    def _layer_user_recommendations(self, emotion):
        print("Layer 1 → User taste recommendations")
        try:
            top_artists = self.sp.current_user_top_artists(
                limit=5).get("items", [])
            top_tracks = self.sp.current_user_top_tracks(
                limit=5).get("items", [])

            seed_artist = top_artists[0]["id"] if top_artists else None
            seed_track = top_tracks[0]["id"] if top_tracks else None
            seed_genre = random.choice(
                self.EMOTION_GENRES.get(emotion, ["pop"]))
            targets = self._convert_targets(emotion)

            rec = self.sp.recommendations(
                seed_genres=[seed_genre],
                seed_artists=[seed_artist] if seed_artist else None,
                seed_tracks=[seed_track] if seed_track else None,
                limit=40,
                **targets
            )
            return [t["uri"] for t in rec.get("tracks", [])]
        except:
            return []

    # -------------------------------
    # LAYER 2 — USER PLAYLIST MATCHING
    # -------------------------------
    def _layer_playlist_matches(self, emotion):
        print("Layer 2 → Matching user playlists")
        try:
            playlists = self.sp.current_user_playlists().get("items", [])
            target = self.EMOTION_TARGETS.get(emotion, {})

            matched = []
            for pl in playlists:
                items = self.sp.playlist_tracks(
                    pl["id"], limit=50).get("items", [])
                track_ids = [t["track"]["id"] for t in items if t["track"]]
                if not track_ids:
                    continue
                features = self.sp.audio_features(track_ids)
                for feat, item in zip(features, items):
                    if feat and self._match_features(feat, target):
                        matched.append(item["track"]["uri"])
            return matched
        except:
            return []

    def _match_features(self, feat, target):
        for key, (low, high) in target.items():
            if key not in feat:
                continue
            if not (low <= feat[key] <= high):
                return False
        return True

    # -------------------------------
    # LAYER 3 — GLOBAL FALLBACK
    # -------------------------------
    def _layer_global_recommendations(self, emotion):
        print("Layer 3 → Global recommendations")
        try:
            seed = random.choice(self.EMOTION_GENRES.get(emotion, ["pop"]))
            targets = self._convert_targets(emotion)
            rec = self.sp.recommendations(
                seed_genres=[seed], limit=50, **targets)
            tracks = rec.get("tracks", [])
            if tracks:
                return [t["uri"] for t in tracks]
        except:
            pass
        try:
            result = self.sp.search(q=f"genre:{seed}", type="track", limit=30)
            return [t["uri"] for t in result["tracks"]["items"]]
        except:
            return []

    # -------------------------------
    # UTILITY — Convert target ranges
    # -------------------------------
    def _convert_targets(self, emotion):
        raw = self.EMOTION_TARGETS.get(emotion, {})
        out = {}
        for k, (low, high) in raw.items():
            mid = (low + high) / 2
            out[f"target_{k}"] = mid
        return out

    # -------------------------------
    # BASIC CONTROLS
    # -------------------------------
    def pause(self):
        try:
            self.sp.pause_playback()
        except:
            pass

    def next(self):
        try:
            self.sp.next_track()
        except:
            pass

    def previous(self):
        """Play previous track (new method)."""
        try:
            self.sp.previous_track()
        except:
            pass
