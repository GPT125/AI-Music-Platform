# Santoor AI Learning Platform

A free-first MusicXML learning platform for Persian Santoor, with a polished React interface, FastAPI backend, private beta login, Santoor-aware mapping, generated accompaniment, and a browser microphone score follower.

The tutorial-video MVP follows the original research plan without a third-party video-generation service: MusicXML is corrected first, Santoor events drive the notation cursor and bridge/octave overlay, audio is derived from the same timeline, and FFmpeg muxes rendered frames plus WAV into MP4. No video API key is required for this deterministic path.

## Local Setup

1. Create a Python environment and install backend dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r backend/requirements.txt
   ```
2. Install frontend dependencies:
   ```bash
   npm install --prefix frontend
   ```
3. Fill `.env` or leave it blank for local SQLite defaults. At minimum for a real private beta, set:
   ```bash
   JWT_SECRET=your-long-random-secret
   INITIAL_ADMIN_EMAIL=you@example.com
   INITIAL_ADMIN_PASSWORD=your-password
   ```
4. Run the API:
   ```bash
   uvicorn backend.app.main:app --reload --port 8000
   ```
5. Run the frontend:
   ```bash
   npm run dev --prefix frontend
   ```

## Render

This repo is configured for a single free Render web service and a free Render Postgres database through `render.yaml`. Render deployment requires a GitHub/GitLab/Bitbucket remote. Free Render Postgres expires after 30 days, so move to a paid database or external free-tier Postgres before storing durable user data.

## Verification

```bash
pytest backend/tests
npm run lint --prefix frontend
npm run typecheck --prefix frontend
npm run test --prefix frontend
npm run build --prefix frontend
docker build -t santoor-ai-learning-platform .
```
