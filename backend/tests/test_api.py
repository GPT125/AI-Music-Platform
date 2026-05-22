from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.auth import hash_password
from backend.app.db import Base, SessionLocal, engine
from backend.app.main import app
from backend.app.models import User


SAMPLE_MUSICXML = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Santoor</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <direction><direction-type><metronome><beat-unit>quarter</beat-unit><per-minute>96</per-minute></metronome></direction-type></direction>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>E</step><alter>-0.5</alter><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>F</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
    </measure>
  </part>
</score-partwise>
"""


def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        db.add(User(email="admin@example.com", password_hash=hash_password("secret"), is_admin=True))
        db.commit()


def login(client: TestClient):
    response = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "secret"})
    assert response.status_code == 200


def test_private_routes_require_authentication():
    reset_db()
    client = TestClient(app)
    response = client.get("/api/projects")
    assert response.status_code == 401


def test_musicxml_upload_maps_santoor_events(tmp_path: Path):
    reset_db()
    client = TestClient(app)
    login(client)
    project = client.post("/api/projects", json={"name": "Radif exercise"}).json()
    response = client.post(
        f"/api/projects/{project['id']}/assets",
        files={"file": ("exercise.musicxml", SAMPLE_MUSICXML.encode("utf-8"), "application/vnd.recordare.musicxml+xml")},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "processed"
    score = client.get(f"/api/projects/{project['id']}/score").json()
    assert score["status"] == "ready"
    assert len(score["events"]) == 3
    assert score["events"][1]["accidental_cents"] == -50
    assert "bridge_id" in score["events"][0]


def test_arrangement_requires_score_then_generates_tracks():
    reset_db()
    client = TestClient(app)
    login(client)
    project = client.post("/api/projects", json={"name": "Orchestra test"}).json()
    empty_response = client.post(f"/api/projects/{project['id']}/arrangements", json={"instruments": ["violin"]})
    assert empty_response.status_code == 400
    client.post(
        f"/api/projects/{project['id']}/assets",
        files={"file": ("exercise.musicxml", SAMPLE_MUSICXML.encode("utf-8"), "application/vnd.recordare.musicxml+xml")},
    )
    response = client.post(
        f"/api/projects/{project['id']}/arrangements",
        json={"instruments": ["violin", "flute", "cello"]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["tracks"]) == 3
    assert payload["tracks"][0]["notes"]

