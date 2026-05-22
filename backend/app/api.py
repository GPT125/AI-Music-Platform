from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.auth import clear_auth_cookie, current_user, set_auth_cookie, verify_password
from backend.app.core.config import get_settings
from backend.app.db import get_db
from backend.app.models import Arrangement, Asset, Job, Project, Score, User
from backend.app.schemas import (
    ArrangementRequest,
    JobCreate,
    LoginRequest,
    ProjectCreate,
    ProjectOut,
    ScoreUpdate,
    UserOut,
)
from backend.app.services.arrangement import generate_arrangement, instrument_catalog
from backend.app.services.musicxml import parse_musicxml_events, read_score_payload
from backend.app.services.santoor import build_santoor_events


router = APIRouter(prefix="/api")
ALLOWED_EXTENSIONS = {".musicxml", ".xml", ".mxl", ".mid", ".midi", ".pdf", ".png", ".jpg", ".jpeg"}


def project_for_user(db: Session, project_id: str, user: User) -> Project:
    project = db.get(Project, project_id)
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def serialize_project(project: Project) -> ProjectOut:
    latest_job = project.jobs[-1] if project.jobs else None
    return ProjectOut(
        id=project.id,
        name=project.name,
        instrument=project.instrument,
        tuning_preset=project.tuning_preset,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
        score_status=project.score.status if project.score else None,
        latest_job_status=latest_job.status if latest_job else None,
    )


@router.post("/auth/login", response_model=UserOut)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> User:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    set_auth_cookie(response, user)
    return user


@router.post("/auth/logout")
def logout(response: Response) -> dict:
    clear_auth_cookie(response)
    return {"ok": True}


@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> User:
    return user


@router.get("/instruments")
def instruments() -> dict:
    return {"instruments": instrument_catalog()}


@router.post("/projects", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(current_user)) -> ProjectOut:
    project = Project(
        owner_id=user.id,
        name=payload.name.strip(),
        instrument=payload.instrument,
        tuning_preset=payload.tuning_preset,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return serialize_project(project)


@router.get("/projects", response_model=List[ProjectOut])
def list_projects(db: Session = Depends(get_db), user: User = Depends(current_user)) -> List[ProjectOut]:
    projects = db.query(Project).filter(Project.owner_id == user.id).order_by(Project.created_at.desc()).all()
    return [serialize_project(project) for project in projects]


@router.post("/projects/{project_id}/assets")
async def upload_asset(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict:
    settings = get_settings()
    project = project_for_user(db, project_id, user)
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    raw = await file.read()
    if len(raw) > settings.upload_max_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File is larger than upload limit")

    storage_dir = Path(settings.storage_dir) / "uploads" / project.id
    storage_dir.mkdir(parents=True, exist_ok=True)
    asset = Asset(
        project_id=project.id,
        filename=file.filename or f"upload{suffix}",
        content_type=file.content_type or "application/octet-stream",
        kind=suffix.lstrip("."),
        storage_path="",
        status="uploaded",
    )
    db.add(asset)
    db.flush()
    storage_path = storage_dir / f"{asset.id}{suffix}"
    storage_path.write_bytes(raw)
    asset.storage_path = str(storage_path)

    job = Job(project_id=project.id, type="ingest", status="running", progress=20, message="Reading uploaded score")
    db.add(job)
    db.flush()

    if suffix in {".musicxml", ".xml", ".mxl"}:
        try:
            musicxml, source_format = read_score_payload(raw, suffix)
            events = parse_musicxml_events(musicxml)
            santoor_events = build_santoor_events(events, project.tuning_preset)
            if project.score:
                score = project.score
                score.musicxml = musicxml
                score.events = santoor_events
                score.source_format = source_format
                score.status = "ready"
                score.meta = {"event_count": len(events), "message": "MusicXML imported"}
                score.updated_at = datetime.utcnow()
            else:
                score = Score(
                    project_id=project.id,
                    source_format=source_format,
                    status="ready",
                    musicxml=musicxml,
                    events=santoor_events,
                    meta={"event_count": len(events), "message": "MusicXML imported"},
                )
                db.add(score)
            asset.status = "processed"
            job.status = "completed"
            job.progress = 100
            job.message = f"Imported {len(events)} score events"
            job.result = {"score_status": "ready", "event_count": len(events)}
        except Exception as exc:
            asset.status = "error"
            job.status = "failed"
            job.progress = 100
            job.message = str(exc)
            job.result = {"error": str(exc)}
    elif suffix in {".mid", ".midi"}:
        asset.status = "needs_musicxml"
        job.status = "completed"
        job.progress = 100
        job.message = "MIDI stored. Import MusicXML for notation-accurate Santoor mapping."
        job.result = {"score_status": "needs_musicxml"}
    else:
        asset.status = "needs_omr"
        status_message = "Image/PDF stored. Configure Audiveris, homr, or oemer to enable automatic OMR."
        if any([settings.omr_audiveris_path, settings.omr_homr_path, settings.omr_oemer_path]):
            status_message = "Image/PDF stored. OMR is configured but asynchronous OMR is not enabled in this free-first service."
        job.status = "completed"
        job.progress = 100
        job.message = status_message
        job.result = {"score_status": "needs_omr"}
        if not project.score:
            db.add(
                Score(
                    project_id=project.id,
                    source_format=suffix.lstrip("."),
                    status="needs_omr",
                    musicxml="",
                    events=[],
                    meta={"message": status_message},
                )
            )
    project.updated_at = datetime.utcnow()
    job.updated_at = datetime.utcnow()
    db.commit()
    return {"asset_id": asset.id, "job_id": job.id, "status": asset.status, "message": job.message}


@router.post("/projects/{project_id}/jobs")
def create_job(
    project_id: str,
    payload: JobCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict:
    project = project_for_user(db, project_id, user)
    job = Job(project_id=project.id, type=payload.type, status="running", progress=25, message="Job started")
    db.add(job)
    db.flush()
    if payload.type in {"normalize", "map"}:
        if not project.score or not project.score.musicxml:
            job.status = "failed"
            job.message = "No MusicXML score is available"
            job.progress = 100
        else:
            events = parse_musicxml_events(project.score.musicxml)
            project.score.events = build_santoor_events(events, project.tuning_preset)
            project.score.status = "ready"
            project.score.updated_at = datetime.utcnow()
            job.status = "completed"
            job.progress = 100
            job.message = f"Mapped {len(events)} Santoor events"
            job.result = {"event_count": len(events)}
    elif payload.type == "arrange":
        if not project.score or not project.score.events:
            job.status = "failed"
            job.message = "No score events are available"
            job.progress = 100
        else:
            tracks = generate_arrangement(project.score.events, [])
            arrangement = Arrangement(project_id=project.id, name="Live Orchestra", instruments=[track["instrument"]["id"] for track in tracks], tracks=tracks)
            db.add(arrangement)
            job.status = "completed"
            job.progress = 100
            job.message = "Generated default orchestra arrangement"
            job.result = {"arrangement_id": arrangement.id}
    else:
        job.status = "completed"
        job.progress = 100
        job.message = "OMR hook checked. Configure an OMR binary before running image/PDF recognition."
    job.updated_at = datetime.utcnow()
    project.updated_at = datetime.utcnow()
    db.commit()
    return {"id": job.id, "status": job.status, "message": job.message, "result": job.result}


@router.get("/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    job = db.get(Job, job_id)
    if not job or job.project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job.id,
        "type": job.type,
        "status": job.status,
        "progress": job.progress,
        "message": job.message,
        "result": job.result,
        "updated_at": job.updated_at.isoformat(),
    }


@router.get("/projects/{project_id}/score")
def get_score(project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    project = project_for_user(db, project_id, user)
    if not project.score:
        return {"status": "empty", "musicxml": "", "events": [], "meta": {}}
    return {
        "status": project.score.status,
        "source_format": project.score.source_format,
        "musicxml": project.score.musicxml,
        "events": project.score.events,
        "meta": project.score.meta,
    }


@router.put("/projects/{project_id}/score")
def update_score(
    project_id: str,
    payload: ScoreUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict:
    project = project_for_user(db, project_id, user)
    if payload.events is not None:
        events = payload.events
    elif payload.musicxml:
        events = build_santoor_events(parse_musicxml_events(payload.musicxml), project.tuning_preset)
    else:
        events = []
    if project.score:
        score = project.score
        score.musicxml = payload.musicxml
        score.events = events
        score.status = payload.status
        score.source_format = "musicxml" if payload.musicxml else score.source_format
        score.updated_at = datetime.utcnow()
    else:
        score = Score(project_id=project.id, source_format="musicxml", status=payload.status, musicxml=payload.musicxml, events=events)
        db.add(score)
    project.updated_at = datetime.utcnow()
    db.commit()
    return {"status": score.status, "event_count": len(events)}


@router.get("/projects/{project_id}/santoor-events")
def get_santoor_events(project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    project = project_for_user(db, project_id, user)
    events = project.score.events if project.score else []
    return {"events": events, "tuning_preset": project.tuning_preset}


@router.post("/projects/{project_id}/arrangements")
def create_arrangement(
    project_id: str,
    payload: ArrangementRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict:
    project = project_for_user(db, project_id, user)
    if not project.score or not project.score.events:
        raise HTTPException(status_code=400, detail="Import a MusicXML score before generating an arrangement")
    tracks = generate_arrangement(project.score.events, payload.instruments, payload.style)
    arrangement = Arrangement(
        project_id=project.id,
        name=payload.name,
        instruments=[track["instrument"]["id"] for track in tracks],
        tracks=tracks,
    )
    db.add(arrangement)
    db.commit()
    return {"id": arrangement.id, "name": arrangement.name, "tracks": arrangement.tracks}

