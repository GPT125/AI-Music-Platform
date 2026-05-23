from __future__ import annotations

from typing import Any, Dict, List, Optional


def build_tutorial_video_plan(
    score_events: List[Dict[str, Any]],
    arrangement_id: Optional[str] = None,
    fps: int = 30,
) -> Dict[str, Any]:
    duration = 0.0
    if score_events:
        duration = max(float(event.get("onset_s", 0)) + float(event.get("duration_s", 0)) for event in score_events)

    cue_frames = []
    for event in score_events[:256]:
        onset = float(event.get("onset_s", 0))
        duration_s = float(event.get("duration_s", 0))
        cue_frames.append(
            {
                "event_id": event.get("id", ""),
                "label": event.get("ui_label") or event.get("note_name") or f"MIDI {event.get('midi_note', 60)}",
                "start_frame": round(onset * fps),
                "end_frame": round((onset + duration_s) * fps),
                "onset_s": round(onset, 4),
                "duration_s": round(duration_s, 4),
                "bridge_id": event.get("bridge_id", ""),
                "region": event.get("region", ""),
                "octave_lane": int(event.get("octave_lane", 0)),
                "highlight": event.get("highlight", {}),
            }
        )

    return {
        "status": "render_plan_ready",
        "renderer": "ffmpeg",
        "requires_api_key": False,
        "api_key_policy": "No video-generation API key is needed for the MVP. The platform renders deterministic frames and muxes them with generated audio locally or in a queued worker.",
        "fps": fps,
        "resolution": {"width": 1280, "height": 720},
        "duration_s": round(duration, 4),
        "frame_count": round(duration * fps),
        "event_count": len(score_events),
        "arrangement_id": arrangement_id,
        "pipeline": [
            "MusicXML correction is the source of truth",
            "SantoorEvent JSON drives bridge, lane, octave, and beat highlights",
            "MIDI/audio is derived from the same event timeline",
            "Frame renderer draws notation cursor and Santoor overlay",
            "FFmpeg muxes rendered frames plus WAV into the final MP4",
        ],
        "artifacts": {
            "musicxml": "score.musicxml",
            "events": "santoor-events.json",
            "audio": "render.wav",
            "frames": "frames/frame-%05d.png",
            "video": "tutorial.mp4",
        },
        "ffmpeg_command": [
            "ffmpeg",
            "-y",
            "-framerate",
            str(fps),
            "-i",
            "frames/frame-%05d.png",
            "-i",
            "render.wav",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "tutorial.mp4",
        ],
        "cues": cue_frames,
    }
