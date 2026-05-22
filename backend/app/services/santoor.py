from __future__ import annotations

from typing import Any, Dict, List


def standard_preset() -> Dict[str, List[Dict[str, Any]]]:
    bridges: Dict[str, List[Dict[str, Any]]] = {}
    base_notes = [50, 52, 53, 55, 57, 59, 60, 62, 64]
    for index, midi in enumerate(base_notes, start=1):
        bridges[f"B{index:02d}"] = [
            {"region": "left", "pitch_cents": midi * 100, "lane": 0},
            {"region": "right", "pitch_cents": (midi + 12) * 100, "lane": 1},
            {"region": "behind-bridge", "pitch_cents": (midi + 24) * 100, "lane": 2},
        ]
    return bridges


TUNING_PRESETS = {"persian_santoor_standard": standard_preset()}


def map_pitch_to_santoor(midi_note: int, accidental_cents: int, preset_name: str = "persian_santoor_standard") -> Dict[str, Any]:
    preset = TUNING_PRESETS.get(preset_name, TUNING_PRESETS["persian_santoor_standard"])
    target = midi_note * 100 + accidental_cents
    candidates = []
    for bridge_id, regions in preset.items():
        for playable in regions:
            distance = abs(playable["pitch_cents"] - target)
            candidates.append((distance, bridge_id, playable))
    distance, bridge_id, playable = min(candidates, key=lambda item: item[0])
    return {
        "bridge_id": bridge_id,
        "region": playable["region"],
        "octave_lane": playable["lane"],
        "mapping_error_cents": distance,
    }


def build_santoor_events(events: List[Dict[str, Any]], preset_name: str = "persian_santoor_standard") -> List[Dict[str, Any]]:
    mapped = []
    for index, event in enumerate(events):
        mapping = map_pitch_to_santoor(
            int(event.get("midi_note", 60)),
            int(event.get("accidental_cents", 0)),
            preset_name,
        )
        mapped.append(
            {
                **event,
                **mapping,
                "ui_label": event.get("note_name", f"MIDI {event.get('midi_note', 60)}"),
                "highlight": {
                    "x": ((int(mapping["bridge_id"][1:]) - 1) % 9) / 8,
                    "y": 0.22 + mapping["octave_lane"] * 0.25,
                    "lane": mapping["octave_lane"],
                    "order": index,
                },
            }
        )
    return mapped

