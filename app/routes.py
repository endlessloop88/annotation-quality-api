from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from . import schemas, services
from .database import get_db

router = APIRouter()


@router.post("/annotators", response_model=schemas.AnnotatorOut, status_code=status.HTTP_201_CREATED)
def create_annotator(data: schemas.AnnotatorCreate, db: Session = Depends(get_db)):
    return services.create_annotator(db, data)


@router.get("/annotators/{annotator_id}", response_model=schemas.AnnotatorOut)
def read_annotator(annotator_id: int, db: Session = Depends(get_db)):
    return services.get_annotator(db, annotator_id)


@router.get("/annotators/{annotator_id}/metrics", response_model=schemas.Metrics)
def annotator_metrics(annotator_id: int, db: Session = Depends(get_db)):
    return services.annotator_metrics(db, annotator_id)


@router.post("/tasks", response_model=schemas.TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(data: schemas.TaskCreate, db: Session = Depends(get_db)):
    return services.create_task(db, data)


@router.get("/tasks/{task_id}", response_model=schemas.TaskOut)
def read_task(task_id: int, db: Session = Depends(get_db)):
    return services.get_task(db, task_id)


@router.post("/submissions", response_model=schemas.SubmissionOut, status_code=status.HTTP_201_CREATED)
def create_submission(data: schemas.SubmissionCreate, db: Session = Depends(get_db)):
    return services.create_submission(db, data)


@router.get("/submissions/{submission_id}", response_model=schemas.SubmissionOut)
def read_submission(submission_id: int, db: Session = Depends(get_db)):
    return services.get_submission(db, submission_id)


@router.post(
    "/submissions/{submission_id}/review",
    response_model=schemas.ReviewOut,
    status_code=status.HTTP_201_CREATED,
)
def review_submission(
    submission_id: int, data: schemas.ReviewCreate, db: Session = Depends(get_db)
):
    return services.review_submission(db, submission_id, data)


@router.get("/projects/{project}/metrics", response_model=schemas.Metrics)
def project_metrics(project: str, db: Session = Depends(get_db)):
    return services.project_metrics(db, project)
