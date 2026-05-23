export type User = {
  id: string;
  email: string;
  is_admin: boolean;
  name: string;
  avatar_url: string;
  auth_provider: string;
};

export type Project = {
  id: string;
  name: string;
  instrument: string;
  tuning_preset: string;
  created_at: string;
  updated_at: string;
  score_status?: string | null;
  latest_job_status?: string | null;
};

export type SantoorEvent = {
  id: string;
  note_name: string;
  midi_note: number;
  accidental_cents: number;
  onset_s: number;
  duration_s: number;
  velocity: number;
  bridge_id: string;
  region: string;
  octave_lane: number;
  mapping_error_cents: number;
  ui_label: string;
  highlight: { x: number; y: number; lane: number; order: number };
};

export type ScorePayload = {
  status: string;
  source_format?: string;
  musicxml: string;
  events: SantoorEvent[];
  meta: Record<string, unknown>;
};

export type Instrument = {
  id: string;
  name: string;
  family: string;
  program: number;
};

export type ArrangementTrack = {
  instrument: Instrument;
  style: string;
  notes: Array<{ midi_note: number; onset_s: number; duration_s: number; velocity: number }>;
  enabled: boolean;
  volume: number;
};

export type ArrangementPayload = {
  id: string;
  name: string;
  tracks: ArrangementTrack[];
};

export type TutorialVideoPlan = {
  status: string;
  renderer: string;
  requires_api_key: boolean;
  api_key_policy: string;
  fps: number;
  resolution: { width: number; height: number };
  duration_s: number;
  frame_count: number;
  event_count: number;
  arrangement_id?: string | null;
  pipeline: string[];
  artifacts: Record<string, string>;
  ffmpeg_command: string[];
  cues: Array<{
    event_id: string;
    label: string;
    start_frame: number;
    end_frame: number;
    onset_s: number;
    duration_s: number;
    bridge_id: string;
    region: string;
    octave_lane: number;
    highlight: SantoorEvent["highlight"];
  }>;
};
