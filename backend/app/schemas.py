from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class UserOut(BaseModel):
    id: str
    email: EmailStr
    is_admin: bool

    model_config = {"from_attributes": True}


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    instrument: str = "santoor"
    tuning_preset: str = "persian_santoor_standard"


class ProjectOut(BaseModel):
    id: str
    name: str
    instrument: str
    tuning_preset: str
    created_at: str
    updated_at: str
    score_status: Optional[str] = None
    latest_job_status: Optional[str] = None


class ScoreUpdate(BaseModel):
    musicxml: str = ""
    events: Optional[List[Dict[str, Any]]] = None
    status: str = "ready"


class JobCreate(BaseModel):
    type: str = Field(pattern="^(normalize|map|arrange|omr)$")


class ArrangementRequest(BaseModel):
    instruments: List[str] = Field(default_factory=list)
    style: str = "balanced"
    name: str = "Live Orchestra"

