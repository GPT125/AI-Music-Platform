import { describe, expect, it } from "vitest";
import { detectPitch, midiToFrequency, updateFollower, type FollowerState } from "./follower";
import type { SantoorEvent } from "../types";

function sine(frequency: number, sampleRate = 44100, length = 2048) {
  const buffer = new Float32Array(length);
  for (let index = 0; index < length; index += 1) {
    buffer[index] = Math.sin((2 * Math.PI * frequency * index) / sampleRate) * 0.7;
  }
  return buffer;
}

const baseState: FollowerState = {
  index: 0,
  confidence: 0,
  detectedPitch: null,
  energy: 0,
  tempoRatio: 1,
  isPaused: true,
};

const events: SantoorEvent[] = [
  {
    id: "n1",
    note_name: "A4",
    midi_note: 69,
    accidental_cents: 0,
    onset_s: 0,
    duration_s: 0.5,
    velocity: 82,
    bridge_id: "B01",
    region: "right",
    octave_lane: 1,
    mapping_error_cents: 0,
    ui_label: "A4",
    highlight: { x: 0, y: 0, lane: 1, order: 0 },
  },
  {
    id: "n2",
    note_name: "B4",
    midi_note: 71,
    accidental_cents: 0,
    onset_s: 0.5,
    duration_s: 0.5,
    velocity: 82,
    bridge_id: "B02",
    region: "right",
    octave_lane: 1,
    mapping_error_cents: 0,
    ui_label: "B4",
    highlight: { x: 0, y: 0, lane: 1, order: 1 },
  },
];

describe("score follower", () => {
  it("detects a synthetic A4 pitch", () => {
    const result = detectPitch(sine(440), 44100);
    expect(result.frequency).toBeTruthy();
    expect(result.frequency!).toBeGreaterThan(430);
    expect(result.frequency!).toBeLessThan(450);
  });

  it("advances and raises confidence for matching score notes", () => {
    const next = updateFollower(baseState, events, midiToFrequency(69), 0.2, 350);
    expect(next.index).toBe(1);
    expect(next.confidence).toBeGreaterThan(0);
    expect(next.isPaused).toBe(false);
  });

  it("pauses when input is silent", () => {
    const next = updateFollower({ ...baseState, confidence: 0.6 }, events, null, 0.001, 100);
    expect(next.isPaused).toBe(true);
    expect(next.confidence).toBeLessThan(0.6);
  });
});

