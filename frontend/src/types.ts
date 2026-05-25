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
  string_material: string;
  course: number;
  strings: number;
  octave_lane: number;
  mapping_error_cents: number;
  playable_midi_note: number;
  playable_accidental_cents: number;
  playable_label: string;
  ui_label: string;
  highlight: { x: number; y: number; lane: number; order: number; hand?: string; strike_angle?: number };
  technique?: { mallet: string; stroke: string; damping: string; resonance_s: number };
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

export type ArrangementNote = { midi_note: number; onset_s: number; duration_s: number; velocity: number; follow_event_id?: string };

export type ArrangementTrack = {
  instrument: Instrument;
  style: string;
  notes: ArrangementNote[];
  enabled: boolean;
  volume: number;
  sample_policy?: string;
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
  views: Array<{
    id: "overhead" | "right_side" | "left_side";
    label: string;
    description: string;
    camera: { x: number; y: number; zoom: number; rotation: number };
  }>;
  performance_model: Record<string, unknown>;
  pipeline: string[];
  artifacts: Record<string, string>;
  ffmpeg_command: string[];
  video_url?: string;
  selected_view?: string;
  cues: Array<{
    event_id: string;
    label: string;
    start_frame: number;
    end_frame: number;
    onset_s: number;
    duration_s: number;
    bridge_id: string;
    region: string;
    string_material: string;
    course: number;
    octave_lane: number;
    highlight: SantoorEvent["highlight"];
    mallet: string;
    resonance_s: number;
    playable_label: string;
  }>;
};

export type AIStatus = {
  configured: boolean;
  active_provider: string | null;
  providers: Array<{ id: string; name: string; model: string }>;
  features: string[];
};

export type AIFeedback = {
  summary: string;
  practice_plan: string[];
  technical_notes: string[];
  rhythm_notes: string[];
  santoor_notes: string[];
  risk_flags: string[];
  confidence: number;
  _provider: string;
  _model: string;
};
