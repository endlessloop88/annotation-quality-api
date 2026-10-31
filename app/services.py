"""Business rules. Kept separate from the HTTP layer so they are easy to test."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models, schemas

STATUS_SUBMITTED = "submitted"
STATUS_ACCEPTED = "accepted"
STATUS_REWORK = "rework"
STATUS_REJECTED = "rejected"


class NotFoundError(Exception):
    """A requested record does not exist."""


class ConflictError(Exception):
    """The request conflicts with the current state of the data."""


# ---- annotators ---------------------------------------------------------


def create_annotator(db: Session, data: schemas.AnnotatorCreate) -> models.Annotator:
    existing = db.scalar(select(models.Annotator).where(models.Annotator.name == data.name))
    if existing is not None:
        raise ConflictError(f"Annotator '{data.name}' already exists")

    annotator = models.Annotator(name=data.name)
    db.add(annotator)
    db.commit()
    db.refresh(annotator)
    return annotator


def get_annotator(db: Session, annotator_id: int) -> models.Annotator:
    annotator = db.get(models.Annotator, annotator_id)
    if annotator is None:
        raise NotFoundError(f"Annotator {annotator_id} not found")
    return annotator


# ---- tasks --------------------------------------------------------------


def create_task(db: Session, data: schemas.TaskCreate) -> models.Task:
    task = models.Task(
        project=data.project,
        guideline_version=data.guideline_version,
        prompt=data.prompt,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task(db: Session, task_id: int) -> models.Task:
    task = db.get(models.Task, task_id)
    if task is None:
        raise NotFoundError(f"Task {task_id} not found")
    return task


# ---- submissions --------------------------------------------------------


def create_submission(db: Session, data: schemas.SubmissionCreate) -> models.Submission:
    """An annotator may submit a task once, and again only after a 'rework' review."""
    get_task(db, data.task_id)
    get_annotator(db, data.annotator_id)

    last = db.scalar(
        select(models.Submission)
        .where(
            models.Submission.task_id == data.task_id,
            models.Submission.annotator_id == data.annotator_id,
        )
        .order_by(models.Submission.attempt.desc())
        .limit(1)
    )
    if last is not None and last.status != STATUS_REWORK:
        raise ConflictError("A submission for this task already exists and is not waiting for rework")

    submission = models.Submission(
        task_id=data.task_id,
        annotator_id=data.annotator_id,
        content=data.content,
        attempt=1 if last is None else last.attempt + 1,
        status=STATUS_SUBMITTED,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


def get_submission(db: Session, submission_id: int) -> models.Submission:
    submission = db.get(models.Submission, submission_id)
    if submission is None:
        raise NotFoundError(f"Submission {submission_id} not found")
    return submission


# ---- reviews ------------------------------------------------------------


def review_submission(
    db: Session, submission_id: int, data: schemas.ReviewCreate
) -> models.Review:
    """A submission is reviewed exactly once; the decision becomes its new status."""
    submission = get_submission(db, submission_id)
    if submission.status != STATUS_SUBMITTED:
        raise ConflictError("This submission has already been reviewed")

    review = models.Review(
        submission_id=submission.id,
        reviewer=data.reviewer,
        decision=data.decision.value,
        score=data.score,
        comment=data.comment,
    )
    submission.status = data.decision.value
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


# ---- metrics ------------------------------------------------------------


def _metrics(db: Session, conditions: list, join_task: bool) -> dict:
    """Quality metrics over a set of submissions.

    approval_rate = accepted / reviewed, rework_rate = rework / reviewed
    (pending submissions are not counted as reviewed).
    """
    counts_query = select(models.Submission.status, func.count(models.Submission.id)).group_by(
        models.Submission.status
    )
    score_query = select(func.avg(models.Review.score)).join(
        models.Submission, models.Review.submission_id == models.Submission.id
    )
    if join_task:
        counts_query = counts_query.join(models.Task, models.Task.id == models.Submission.task_id)
        score_query = score_query.join(models.Task, models.Task.id == models.Submission.task_id)
    for condition in conditions:
        counts_query = counts_query.where(condition)
        score_query = score_query.where(condition)

    counts = {status: total for status, total in db.execute(counts_query).all()}
    average = db.scalar(score_query)

    accepted = counts.get(STATUS_ACCEPTED, 0)
    rework = counts.get(STATUS_REWORK, 0)
    rejected = counts.get(STATUS_REJECTED, 0)
    pending = counts.get(STATUS_SUBMITTED, 0)
    reviewed = accepted + rework + rejected

    return {
        "submissions": reviewed + pending,
        "reviewed": reviewed,
        "accepted": accepted,
        "rework": rework,
        "rejected": rejected,
        "pending": pending,
        "approval_rate": round(accepted / reviewed * 100, 1) if reviewed else 0.0,
        "rework_rate": round(rework / reviewed * 100, 1) if reviewed else 0.0,
        "average_score": round(float(average), 1) if average is not None else None,
    }


def annotator_metrics(db: Session, annotator_id: int) -> dict:
    get_annotator(db, annotator_id)
    return _metrics(db, [models.Submission.annotator_id == annotator_id], join_task=False)


def project_metrics(db: Session, project: str) -> dict:
    task_count = db.scalar(select(func.count(models.Task.id)).where(models.Task.project == project))
    if not task_count:
        raise NotFoundError(f"Project '{project}' not found")
    return _metrics(db, [models.Task.project == project], join_task=True)
