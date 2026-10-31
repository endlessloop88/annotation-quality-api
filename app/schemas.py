from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Decision(str, Enum):
    accepted = "accepted"
    rework = "rework"
    rejected = "rejected"


class AnnotatorCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class AnnotatorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime


class TaskCreate(BaseModel):
    project: str = Field(min_length=1, max_length=100)
    guideline_version: str = Field(default="v1", max_length=20)
    prompt: str = Field(min_length=1)


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project: str
    guideline_version: str
    prompt: str
    created_at: datetime


class SubmissionCreate(BaseModel):
    task_id: int
    annotator_id: int
    content: str = Field(min_length=1)


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    annotator_id: int
    content: str
    attempt: int
    status: str
    created_at: datetime


class ReviewCreate(BaseModel):
    reviewer: str = Field(min_length=2, max_length=100)
    decision: Decision
    score: int = Field(ge=0, le=100)
    comment: str | None = None


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    submission_id: int
    reviewer: str
    decision: str
    score: int
    comment: str | None
    created_at: datetime


class Metrics(BaseModel):
    submissions: int
    reviewed: int
    accepted: int
    rework: int
    rejected: int
    pending: int
    approval_rate: float
    rework_rate: float
    average_score: float | None
