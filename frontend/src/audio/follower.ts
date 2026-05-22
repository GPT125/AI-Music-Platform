import type { SantoorEvent } from "../types";

export type FollowerState = {
  index: number;
  confidence: number;
  detectedPitch: number | null;
  energy: number;
  tempoRatio: number;
  isPaused: boolean;
};

export function midiToFrequency(midi: number): number {
  return 440 * 2 ** ((midi - 69) / 12);
}

export function frequencyToMidi(frequency: number): number {
  return Math.round(69 + 12 * Math.log2(frequency / 440));
}

export function detectPitch(buffer: Float32Array, sampleRate: number): { frequency: number | null; energy: number } {
  let rms = 0;
  for (let i = 0; i < buffer.length; i += 1) rms += buffer[i] * buffer[i];
  rms = Math.sqrt(rms / buffer.length);
  if (rms < 0.012) return { frequency: null, energy: rms };

  let bestOffset = -1;
  let bestCorrelation = 0;
  const minOffset = Math.floor(sampleRate / 900);
  const maxOffset = Math.floor(sampleRate / 70);
  const correlations: number[] = [];
  for (let offset = minOffset; offset <= maxOffset; offset += 1) {
    let correlation = 0;
    let leftEnergy = 0;
    let rightEnergy = 0;
    for (let i = 0; i < buffer.length - offset; i += 1) {
      correlation += buffer[i] * buffer[i + offset];
      leftEnergy += buffer[i] * buffer[i];
      rightEnergy += buffer[i + offset] * buffer[i + offset];
    }
    correlation = correlation / Math.sqrt(leftEnergy * rightEnergy);
    correlations[offset] = correlation;
    if (correlation > bestCorrelation) {
      bestCorrelation = correlation;
      bestOffset = offset;
    }
  }
  if (bestOffset <= 0 || bestCorrelation < 0.45) return { frequency: null, energy: rms };
  for (let offset = minOffset + 1; offset < maxOffset - 1; offset += 1) {
    const value = correlations[offset] || 0;
    if (value > bestCorrelation * 0.82 && value > (correlations[offset - 1] || 0) && value >= (correlations[offset + 1] || 0)) {
      bestOffset = offset;
      break;
    }
  }
  return { frequency: sampleRate / bestOffset, energy: rms };
}

export function updateFollower(
  previous: FollowerState,
  events: SantoorEvent[],
  detectedFrequency: number | null,
  energy: number,
  elapsedMs: number,
): FollowerState {
  if (events.length === 0) return previous;
  if (!detectedFrequency || energy < 0.012) {
    return { ...previous, confidence: Math.max(0, previous.confidence - 0.08), energy, isPaused: true };
  }
  const detectedMidi = frequencyToMidi(detectedFrequency);
  const searchWindow = events.slice(previous.index, Math.min(events.length, previous.index + 5));
  let bestIndex = previous.index;
  let bestDistance = 99;
  searchWindow.forEach((event, offset) => {
    const distance = Math.abs(event.midi_note - detectedMidi);
    if (distance < bestDistance) {
      bestDistance = distance;
      bestIndex = previous.index + offset;
    }
  });
  const noteMatch = bestDistance <= 1;
  const expectedDuration = Math.max(events[previous.index]?.duration_s ?? 0.5, 0.2);
  const elapsedRatio = elapsedMs / 1000 / expectedDuration;
  const tempoRatio = Math.max(0.45, Math.min(1.8, noteMatch ? elapsedRatio || previous.tempoRatio : previous.tempoRatio * 0.96));
  const shouldAdvance = noteMatch && (bestIndex > previous.index || elapsedRatio > 0.55);
  return {
    index: shouldAdvance ? Math.min(events.length - 1, bestIndex + 1) : previous.index,
    confidence: noteMatch ? Math.min(1, previous.confidence + 0.14) : Math.max(0, previous.confidence - 0.12),
    detectedPitch: detectedMidi,
    energy,
    tempoRatio,
    isPaused: false,
  };
}
