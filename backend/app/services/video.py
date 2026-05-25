from __future__ import annotations

import math
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np


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


Color = tuple[int, int, int]


def _set_pixel(buffer: bytearray, width: int, height: int, x: int, y: int, color: Color) -> None:
    if x < 0 or x >= width or y < 0 or y >= height:
        return
    offset = (y * width + x) * 3
    buffer[offset : offset + 3] = bytes(color)


def _rect(buffer: bytearray, width: int, height: int, x0: int, y0: int, x1: int, y1: int, color: Color) -> None:
    left, right = sorted((max(0, x0), min(width - 1, x1)))
    top, bottom = sorted((max(0, y0), min(height - 1, y1)))
    row = bytes(color) * (right - left + 1)
    for y in range(top, bottom + 1):
        start = (y * width + left) * 3
        buffer[start : start + len(row)] = row


def _circle(buffer: bytearray, width: int, height: int, cx: int, cy: int, radius: int, color: Color) -> None:
    radius_sq = radius * radius
    for y in range(cy - radius, cy + radius + 1):
        for x in range(cx - radius, cx + radius + 1):
            if (x - cx) * (x - cx) + (y - cy) * (y - cy) <= radius_sq:
                _set_pixel(buffer, width, height, x, y, color)


def _line(buffer: bytearray, width: int, height: int, x0: int, y0: int, x1: int, y1: int, color: Color, thickness: int = 2) -> None:
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        _circle(buffer, width, height, x, y, max(1, thickness), color)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def _point_in_polygon(x: int, y: int, points: list[tuple[int, int]]) -> bool:
    inside = False
    j = len(points) - 1
    for i, point in enumerate(points):
        xi, yi = point
        xj, yj = points[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / max(yj - yi, 0.0001) + xi):
            inside = not inside
        j = i
    return inside


def _polygon(buffer: bytearray, width: int, height: int, points: list[tuple[int, int]], color: Color) -> None:
    min_x = max(0, min(point[0] for point in points))
    max_x = min(width - 1, max(point[0] for point in points))
    min_y = max(0, min(point[1] for point in points))
    max_y = min(height - 1, max(point[1] for point in points))
    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            if _point_in_polygon(x, y, points):
                _set_pixel(buffer, width, height, x, y, color)


SEGMENTS: dict[str, tuple[str, ...]] = {
    "0": ("a", "b", "c", "d", "e", "f"),
    "1": ("b", "c"),
    "2": ("a", "b", "g", "e", "d"),
    "3": ("a", "b", "c", "d", "g"),
    "4": ("f", "g", "b", "c"),
    "5": ("a", "f", "g", "c", "d"),
    "6": ("a", "f", "g", "e", "c", "d"),
    "7": ("a", "b", "c"),
    "8": ("a", "b", "c", "d", "e", "f", "g"),
    "9": ("a", "b", "c", "d", "f", "g"),
    "-": ("g",),
}


def _digit(buffer: bytearray, width: int, height: int, x: int, y: int, char: str, color: Color, scale: int = 3) -> None:
    w = 4 * scale
    h = 8 * scale
    t = max(1, scale)
    segments = SEGMENTS.get(char, ())
    if "a" in segments:
        _rect(buffer, width, height, x + t, y, x + w - t, y + t, color)
    if "b" in segments:
        _rect(buffer, width, height, x + w - t, y + t, x + w, y + h // 2 - t, color)
    if "c" in segments:
        _rect(buffer, width, height, x + w - t, y + h // 2 + t, x + w, y + h - t, color)
    if "d" in segments:
        _rect(buffer, width, height, x + t, y + h - t, x + w - t, y + h, color)
    if "e" in segments:
        _rect(buffer, width, height, x, y + h // 2 + t, x + t, y + h - t, color)
    if "f" in segments:
        _rect(buffer, width, height, x, y + t, x + t, y + h // 2 - t, color)
    if "g" in segments:
        _rect(buffer, width, height, x + t, y + h // 2, x + w - t, y + h // 2 + t, color)


def _text(buffer: bytearray, width: int, height: int, x: int, y: int, text: str, color: Color, scale: int = 3) -> None:
    cursor = x
    for char in text:
        if char.isdigit() or char == "-":
            _digit(buffer, width, height, cursor, y, char, color, scale)
            cursor += 6 * scale
        else:
            _rect(buffer, width, height, cursor, y + 7 * scale, cursor + 3 * scale, y + 8 * scale, color)
            cursor += 5 * scale


def _cue_at(cues: list[Dict[str, Any]], time_s: float) -> Dict[str, Any]:
    for cue in cues:
        if cue["onset_s"] <= time_s <= cue["onset_s"] + max(cue["duration_s"], 0.18):
            return cue
    past = [cue for cue in cues if cue["onset_s"] <= time_s]
    return past[-1] if past else cues[0]


def _draw_frame(width: int, height: int, cues: list[Dict[str, Any]], time_s: float, duration_s: float, view: str) -> bytes:
    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    canvas[:, :] = (20, 28, 30)
    canvas[540:, :] = (238, 232, 219)
    cue = _cue_at(cues, time_s)

    def rect(x0: int, y0: int, x1: int, y1: int, color: Color) -> None:
        x0, x1 = sorted((max(0, x0), min(width, x1)))
        y0, y1 = sorted((max(0, y0), min(height, y1)))
        canvas[y0:y1, x0:x1] = color

    def circle(cx: int, cy: int, radius: int, color: Color) -> None:
        x0, x1 = max(0, cx - radius), min(width, cx + radius + 1)
        y0, y1 = max(0, cy - radius), min(height, cy + radius + 1)
        if x0 >= x1 or y0 >= y1:
            return
        yy, xx = np.ogrid[y0:y1, x0:x1]
        mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= radius * radius
        canvas[y0:y1, x0:x1][mask] = color

    def line(x0: int, y0: int, x1: int, y1: int, color: Color, thickness: int = 2) -> None:
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        xs = np.linspace(x0, x1, steps).astype(int)
        ys = np.linspace(y0, y1, steps).astype(int)
        for x, y in zip(xs[:: max(1, thickness)], ys[:: max(1, thickness)]):
            circle(int(x), int(y), thickness, color)

    def trapezoid(points: list[tuple[int, int]], color: Color) -> None:
        top_left, top_right, bottom_right, bottom_left = points
        for y in range(max(0, min(top_left[1], top_right[1])), min(height, max(bottom_left[1], bottom_right[1]))):
            span = max(1, bottom_left[1] - top_left[1])
            ratio = max(0.0, min(1.0, (y - top_left[1]) / span))
            left = int(top_left[0] * (1 - ratio) + bottom_left[0] * ratio)
            right = int(top_right[0] * (1 - ratio) + bottom_right[0] * ratio)
            if left > right:
                left, right = right, left
            canvas[y, max(0, left) : min(width, right)] = color

    if view == "left_side":
        body = [(120, 170), (1100, 115), (1180, 475), (70, 510)]
    elif view == "right_side":
        body = [(95, 120), (1135, 180), (1210, 510), (150, 455)]
    else:
        body = [(135, 145), (1145, 145), (1060, 500), (220, 500)]
    trapezoid([(point[0], point[1] + 10) for point in body], (166, 113, 58))
    trapezoid(body, (204, 159, 90))

    for index in range(18):
        ratio = index / 17
        x_top = int(body[0][0] * (1 - ratio) + body[1][0] * ratio)
        y_top = int(body[0][1] * (1 - ratio) + body[1][1] * ratio)
        x_bottom = int(body[3][0] * (1 - ratio) + body[2][0] * ratio)
        y_bottom = int(body[3][1] * (1 - ratio) + body[2][1] * ratio)
        color = (245, 219, 135) if index < 9 else (225, 231, 230)
        line(x_top, y_top, x_bottom, y_bottom, color, 1)
        if index % 2 == 0:
            bridge_x = int((x_top + x_bottom) / 2)
            bridge_y = int((y_top + y_bottom) / 2)
            rect(bridge_x - 4, bridge_y - 42, bridge_x + 4, bridge_y + 42, (74, 49, 31))

    bridge_num = max(1, min(18, int(str(cue.get("bridge_id", "B01"))[1:] or 1)))
    lane = max(0, min(2, int(cue.get("octave_lane", 0))))
    strike_x = int(130 + (bridge_num - 1) * 58)
    strike_y = int(240 + lane * 82)
    if view == "right_side":
        strike_y += 34
    elif view == "left_side":
        strike_y -= 18

    pulse = max(0.0, 1.0 - abs(time_s - float(cue["onset_s"])) / 0.22)
    circle(strike_x, strike_y, 18 + int(22 * pulse), (44, 177, 154))
    circle(strike_x, strike_y, 8 + int(8 * pulse), (244, 199, 92))
    active_right = cue.get("mallet") != "left"
    line(940, 95, strike_x + 18 if active_right else 760, strike_y - 4 if active_right else 230, (218, 190, 140), 5)
    line(360, 92, strike_x - 18 if not active_right else 520, strike_y + 16 if not active_right else 245, (218, 190, 140), 5)
    circle(940, 95, 34, (188, 128, 88))
    circle(360, 92, 34, (188, 128, 88))
    circle(strike_x + 18 if active_right else 760, strike_y - 4 if active_right else 230, 10, (248, 232, 188))
    circle(strike_x - 18 if not active_right else 520, strike_y + 16 if not active_right else 245, 10, (248, 232, 188))

    progress = int((time_s / max(duration_s, 0.1)) * (width - 120))
    rect(60, 606, width - 60, 622, (207, 198, 183))
    rect(60, 606, 60 + progress, 622, (35, 105, 95))
    return canvas.tobytes()


def _draw_frame_legacy(width: int, height: int, cues: list[Dict[str, Any]], time_s: float, duration_s: float, view: str) -> bytes:
    buffer = bytearray([245, 241, 232] * width * height)
    _rect(buffer, width, height, 0, 0, width - 1, height - 1, (20, 28, 30))
    _rect(buffer, width, height, 0, 540, width - 1, height - 1, (238, 232, 219))
    cue = _cue_at(cues, time_s)

    if view == "left_side":
        body = [(120, 170), (1100, 115), (1180, 475), (70, 510)]
    elif view == "right_side":
        body = [(95, 120), (1135, 180), (1210, 510), (150, 455)]
    else:
        body = [(135, 145), (1145, 145), (1060, 500), (220, 500)]
    _polygon(buffer, width, height, body, (204, 159, 90))
    _polygon(buffer, width, height, [(point[0], point[1] + 10) for point in body], (166, 113, 58))

    for index in range(18):
        ratio = index / 17
        x_top = int(body[0][0] * (1 - ratio) + body[1][0] * ratio)
        y_top = int(body[0][1] * (1 - ratio) + body[1][1] * ratio)
        x_bottom = int(body[3][0] * (1 - ratio) + body[2][0] * ratio)
        y_bottom = int(body[3][1] * (1 - ratio) + body[2][1] * ratio)
        color = (245, 219, 135) if index < 9 else (225, 231, 230)
        _line(buffer, width, height, x_top, y_top, x_bottom, y_bottom, color, 1)
        if index % 2 == 0:
            bridge_x = int((x_top + x_bottom) / 2)
            bridge_y = int((y_top + y_bottom) / 2)
            _rect(buffer, width, height, bridge_x - 4, bridge_y - 42, bridge_x + 4, bridge_y + 42, (74, 49, 31))

    bridge_num = max(1, min(18, int(str(cue.get("bridge_id", "B01"))[1:] or 1)))
    lane = max(0, min(2, int(cue.get("octave_lane", 0))))
    strike_x = int(130 + (bridge_num - 1) * 58)
    strike_y = int(240 + lane * 82)
    if view == "right_side":
        strike_y += 34
    elif view == "left_side":
        strike_y -= 18

    pulse = max(0.0, 1.0 - abs(time_s - float(cue["onset_s"])) / 0.22)
    _circle(buffer, width, height, strike_x, strike_y, 18 + int(22 * pulse), (44, 177, 154))
    _circle(buffer, width, height, strike_x, strike_y, 8 + int(8 * pulse), (244, 199, 92))

    right_base = (940, 95)
    left_base = (360, 92)
    right_tip = (strike_x + 18, strike_y - 4)
    left_tip = (strike_x - 18, strike_y + 16)
    active_right = cue.get("mallet") != "left"
    _line(buffer, width, height, right_base[0], right_base[1], right_tip[0] if active_right else 760, right_tip[1] if active_right else 230, (218, 190, 140), 5)
    _line(buffer, width, height, left_base[0], left_base[1], left_tip[0] if not active_right else 520, left_tip[1] if not active_right else 245, (218, 190, 140), 5)
    _circle(buffer, width, height, right_base[0], right_base[1], 34, (188, 128, 88))
    _circle(buffer, width, height, left_base[0], left_base[1], 34, (188, 128, 88))
    _circle(buffer, width, height, right_tip[0] if active_right else 760, right_tip[1] if active_right else 230, 10, (248, 232, 188))
    _circle(buffer, width, height, left_tip[0] if not active_right else 520, left_tip[1] if not active_right else 245, 10, (248, 232, 188))

    progress = int((time_s / max(duration_s, 0.1)) * (width - 120))
    _rect(buffer, width, height, 60, 606, width - 60, 622, (207, 198, 183))
    _rect(buffer, width, height, 60, 606, 60 + progress, 622, (35, 105, 95))
    _text(buffer, width, height, 70, 640, f"{int(time_s * 10) / 10}", (35, 43, 46), 4)
    _text(buffer, width, height, 560, 640, f"B{bridge_num}", (35, 43, 46), 5)
    _text(buffer, width, height, 930, 640, str(cue.get("course", 0)), (35, 43, 46), 4)
    _text(buffer, width, height, 70, 48, str(cue.get("label", ""))[:8], (238, 232, 219), 5)
    return bytes(buffer)


def _write_wav(path: Path, cues: list[Dict[str, Any]], duration_s: float, sample_rate: int = 44100) -> None:
    total = max(1, int((duration_s + 0.4) * sample_rate))
    samples = [0.0] * total
    for cue in cues:
        start = int(float(cue["onset_s"]) * sample_rate)
        frequency = 220.0 * (2 ** ((int(cue.get("course", 9)) - 9) / 12))
        for index in range(start, min(total, start + int(0.42 * sample_rate))):
            age = (index - start) / sample_rate
            envelope = math.exp(-age * 7)
            samples[index] += math.sin(2 * math.pi * frequency * age) * envelope * 0.28
            samples[index] += math.sin(2 * math.pi * frequency * 2.01 * age) * envelope * 0.12
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        data = bytearray()
        for sample in samples:
            value = max(-1.0, min(1.0, sample))
            data.extend(int(value * 32767).to_bytes(2, "little", signed=True))
        handle.writeframes(data)


def render_tutorial_video(
    score_events: List[Dict[str, Any]],
    output_dir: str,
    arrangement_id: Optional[str] = None,
    fps: int = 24,
    view: str = "left_side",
) -> Dict[str, Any]:
    plan = build_tutorial_video_plan(score_events, arrangement_id, fps)
    if not plan["cues"]:
        raise ValueError("No Santoor events are available for video rendering.")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required to render MP4 video.")

    root = Path(output_dir)
    frames_dir = root / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for old_frame in frames_dir.glob("frame-*.ppm"):
        old_frame.unlink()

    width = int(plan["resolution"]["width"])
    height = int(plan["resolution"]["height"])
    duration_s = min(max(float(plan["duration_s"]), 1.2), 45.0)
    frame_count = max(1, int(math.ceil(duration_s * fps)))
    for frame_index in range(frame_count):
        frame_path = frames_dir / f"frame-{frame_index:05d}.ppm"
        frame_bytes = _draw_frame(width, height, plan["cues"], frame_index / fps, duration_s, view)
        with frame_path.open("wb") as handle:
            handle.write(f"P6\n{width} {height}\n255\n".encode("ascii"))
            handle.write(frame_bytes)

    audio_path = root / "tutorial.wav"
    video_path = root / "tutorial.mp4"
    _write_wav(audio_path, plan["cues"], duration_s)
    command = [
        ffmpeg,
        "-y",
        "-framerate",
        str(fps),
        "-i",
        str(frames_dir / "frame-%05d.ppm"),
        "-i",
        str(audio_path),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(video_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False, timeout=180)
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "FFmpeg failed without output"
        raise RuntimeError(message[-1200:])

    plan["status"] = "rendered"
    plan["renderer"] = "local_ffmpeg_mp4"
    plan["frame_count"] = frame_count
    plan["duration_s"] = round(duration_s, 4)
    plan["artifacts"]["audio"] = str(audio_path)
    plan["artifacts"]["video"] = str(video_path)
    plan["artifacts"]["frames"] = str(frames_dir / "frame-%05d.ppm")
    plan["selected_view"] = view
    plan["ffmpeg_command"] = command
    return plan
