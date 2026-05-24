from __future__ import annotations

from typing import Any, Dict, List, Optional


CAMERA_VIEWS = [
    {
        "id": "overhead",
        "label": "High hand view",
        "description": "Top-down performer view showing both mallets, all bridges, and exact strike timing.",
        "camera": {"x": 0.5, "y": 0.08, "zoom": 1.0, "rotation": 0},
    },
    {
        "id": "right_side",
        "label": "Right side view",
        "description": "Treble-side angle focused on white strings, right-hand lead strikes, and rebound.",
        "camera": {"x": 0.82, "y": 0.36, "zoom": 1.18, "rotation": -11},
    },
    {
        "id": "left_side",
        "label": "Left side view",
        "description": "Bass-side angle focused on yellow strings, left-hand answers, and low-register resonance.",
        "camera": {"x": 0.18, "y": 0.38, "zoom": 1.18, "rotation": 11},
    },
]


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
                "string_material": event.get("string_material", ""),
                "course": event.get("course", 0),
                "octave_lane": int(event.get("octave_lane", 0)),
                "highlight": event.get("highlight", {}),
                "mallet": event.get("technique", {}).get("mallet", "right"),
                "resonance_s": event.get("technique", {}).get("resonance_s", 2.0),
                "playable_label": event.get("playable_label", event.get("ui_label")),
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
        "views": CAMERA_VIEWS,
        "performance_model": {
            "instrument": "Persian Santoor",
            "strings": 72,
            "courses": 18,
            "bridges": 18,
            "mallets": 2,
            "strike_rendering": "Each cue contains bridge, lane, mallet hand, start frame, end frame, and resonance tail for deterministic animation.",
        },
        "pipeline": [
            "Printed PDF/image is recognized by configured Audiveris OMR, or MusicXML is imported directly",
            "Correction MusicXML is the source of truth",
            "SantoorEvent JSON drives bridge, lane, octave, mallet hand, and beat highlights",
            "Three deterministic camera views render from the same cue timeline",
            "MIDI/audio is derived from the same event timeline",
            "FFmpeg can mux rendered frames plus WAV into the final MP4 when a worker/native runtime is available",
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
