from __future__ import annotations

from typing import Any, Dict, List


STEP_LABELS = {
    0: "C",
    1: "C#",
    2: "D",
    3: "Eb",
    4: "E",
    5: "F",
    6: "F#",
    7: "G",
    8: "Ab",
    9: "A",
    10: "Bb",
    11: "B",
}


def note_label(midi_note: int, cents: int = 0) -> str:
    octave = midi_note // 12 - 1
    suffix = ""
    if cents == -50:
        suffix = " koron"
    elif cents == 50:
        suffix = " sori"
    elif cents:
        suffix = f" {cents:+d}c"
    return f"{STEP_LABELS[midi_note % 12]}{octave}{suffix}"


def standard_preset() -> Dict[str, List[Dict[str, Any]]]:
    bridges: Dict[str, List[Dict[str, Any]]] = {}
    # Practical 9-bridge G/Sol Santoor model. Persian santur is modal and retuned
    # per piece; this preset keeps the common three-octave layout and includes
    # quarter-tone variants used by Shur/Homayoun style repertoire.
    base_notes = [43, 45, 47, 48, 50, 52, 53, 55, 57]
    quarter_adjustments = {
        2: -50,  # B koron
        5: -50,  # E koron
        7: 50,   # F sori option
    }
    for index, midi in enumerate(base_notes, start=1):
        cents = quarter_adjustments.get(index, 0)
        bridges[f"B{index:02d}"] = [
            {
                "region": "yellow_bass",
                "string_material": "bronze",
                "pitch_cents": midi * 100 + cents,
                "lane": 0,
                "course": index,
                "strings": 4,
            },
            {
                "region": "white_middle",
                "string_material": "steel",
                "pitch_cents": (midi + 12) * 100 + cents,
                "lane": 1,
                "course": index + 9,
                "strings": 4,
            },
            {
                "region": "white_behind_bridge",
                "string_material": "steel",
                "pitch_cents": (midi + 24) * 100 + cents,
                "lane": 2,
                "course": index + 18,
                "strings": 4,
            },
        ]
    return bridges


def western_chromatic_preset() -> Dict[str, List[Dict[str, Any]]]:
    bridges: Dict[str, List[Dict[str, Any]]] = {}
    base_notes = [43, 45, 47, 48, 50, 52, 54, 55, 57]
    for index, midi in enumerate(base_notes, start=1):
        bridges[f"B{index:02d}"] = [
            {"region": "yellow_bass", "string_material": "bronze", "pitch_cents": midi * 100, "lane": 0, "course": index, "strings": 4},
            {"region": "white_middle", "string_material": "steel", "pitch_cents": (midi + 12) * 100, "lane": 1, "course": index + 9, "strings": 4},
            {"region": "white_behind_bridge", "string_material": "steel", "pitch_cents": (midi + 24) * 100, "lane": 2, "course": index + 18, "strings": 4},
        ]
    return bridges


TUNING_PRESETS = {
    "persian_santoor_standard": standard_preset(),
    "western_g_santoor": western_chromatic_preset(),
}


def map_pitch_to_santoor(midi_note: int, accidental_cents: int, preset_name: str = "persian_santoor_standard") -> Dict[str, Any]:
    preset = TUNING_PRESETS.get(preset_name, TUNING_PRESETS["persian_santoor_standard"])
    target = midi_note * 100 + accidental_cents
    candidates = []
    for bridge_id, regions in preset.items():
        for playable in regions:
            distance = abs(playable["pitch_cents"] - target)
            candidates.append((distance, bridge_id, playable))
    distance, bridge_id, playable = min(candidates, key=lambda item: item[0])
    playable_cents = int(playable["pitch_cents"])
    playable_midi = round(playable_cents / 100)
    playable_accidental_cents = playable_cents - playable_midi * 100
    return {
        "bridge_id": bridge_id,
        "region": playable["region"],
        "string_material": playable["string_material"],
        "course": playable["course"],
        "strings": playable["strings"],
        "octave_lane": playable["lane"],
        "mapping_error_cents": distance,
        "playable_midi_note": playable_midi,
        "playable_accidental_cents": playable_accidental_cents,
        "playable_label": note_label(playable_midi, playable_accidental_cents),
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
                    "hand": "right" if index % 2 == 0 else "left",
                    "strike_angle": -18 if index % 2 == 0 else 18,
                },
                "technique": {
                    "mallet": "right" if index % 2 == 0 else "left",
                    "stroke": "single",
                    "damping": "let_ring",
                    "resonance_s": 2.4 if mapping["string_material"] == "steel" else 1.7,
                },
            }
        )
    return mapped


def tuning_summary(preset_name: str = "persian_santoor_standard") -> Dict[str, Any]:
    preset = TUNING_PRESETS.get(preset_name, TUNING_PRESETS["persian_santoor_standard"])
    rows = []
    for bridge_id, playables in preset.items():
        rows.append(
            {
                "bridge_id": bridge_id,
                "notes": [
                    {
                        "region": playable["region"],
                        "material": playable["string_material"],
                        "label": note_label(round(playable["pitch_cents"] / 100), playable["pitch_cents"] - round(playable["pitch_cents"] / 100) * 100),
                        "course": playable["course"],
                        "strings": playable["strings"],
                    }
                    for playable in playables
                ],
            }
        )
    return {
        "preset": preset_name,
        "instrument": "Persian Santoor / Santur",
        "bridges": 18,
        "courses": 18,
        "strings": 72,
        "rows": 2,
        "octave_lanes": 3,
        "notes": rows,
    }
