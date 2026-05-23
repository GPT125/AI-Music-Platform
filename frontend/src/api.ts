import type { ArrangementPayload, Instrument, Project, ScorePayload, TutorialVideoPlan, User } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: {
      ...(init.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(init.headers || {}),
    },
    ...init,
  });
  if (!response.ok) {
    let message = response.statusText;
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {
      // Keep the HTTP status text.
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export const api = {
  me: () => request<User>("/api/auth/me"),
  googleStartUrl: () => `${API_BASE}/api/auth/google/start`,
  googleConfig: () => request<{ client_id: string; configured: boolean }>("/api/auth/google/config"),
  googleCredential: (credential: string) =>
    request<User>("/api/auth/google/credential", { method: "POST", body: JSON.stringify({ credential }) }),
  logout: () => request<{ ok: boolean }>("/api/auth/logout", { method: "POST" }),
  projects: () => request<Project[]>("/api/projects"),
  createProject: (name: string) =>
    request<Project>("/api/projects", { method: "POST", body: JSON.stringify({ name, instrument: "santoor" }) }),
  uploadAsset: (projectId: string, file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<{ asset_id: string; job_id: string; status: string; message: string }>(
      `/api/projects/${projectId}/assets`,
      { method: "POST", body },
    );
  },
  score: (projectId: string) => request<ScorePayload>(`/api/projects/${projectId}/score`),
  updateScore: (projectId: string, musicxml: string) =>
    request<{ status: string; event_count: number }>(`/api/projects/${projectId}/score`, {
      method: "PUT",
      body: JSON.stringify({ musicxml, status: "ready" }),
    }),
  instruments: () => request<{ instruments: Instrument[] }>("/api/instruments"),
  arrange: (projectId: string, instruments: string[]) =>
    request<ArrangementPayload>(`/api/projects/${projectId}/arrangements`, {
      method: "POST",
      body: JSON.stringify({ instruments, style: "balanced", name: "Live Orchestra" }),
    }),
  tutorialVideo: (projectId: string, arrangementId?: string) =>
    request<{ job_id: string; message: string; render_plan: TutorialVideoPlan }>(`/api/projects/${projectId}/tutorial-video`, {
      method: "POST",
      body: JSON.stringify({ arrangement_id: arrangementId ?? null, fps: 30 }),
    }),
};
