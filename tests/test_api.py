def make_annotator(client, name="alice"):
    response = client.post("/annotators", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def make_task(client, project="demo", prompt="Label the sentiment of the text"):
    response = client.post("/tasks", json={"project": project, "prompt": prompt})
    assert response.status_code == 201
    return response.json()["id"]


def submit(client, task_id, annotator_id, content="positive"):
    return client.post(
        "/submissions",
        json={"task_id": task_id, "annotator_id": annotator_id, "content": content},
    )


def review(client, submission_id, decision, score=80):
    return client.post(
        f"/submissions/{submission_id}/review",
        json={"reviewer": "reviewer1", "decision": decision, "score": score},
    )


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_duplicate_annotator_is_rejected(client):
    make_annotator(client, "alice")
    response = client.post("/annotators", json={"name": "alice"})
    assert response.status_code == 409


def test_missing_records_return_404(client):
    assert client.get("/annotators/999").status_code == 404
    assert client.get("/tasks/999").status_code == 404
    assert client.get("/submissions/999").status_code == 404
    assert client.get("/projects/unknown/metrics").status_code == 404
    assert submit(client, task_id=999, annotator_id=999).status_code == 404


def test_accepted_review_updates_submission_status(client):
    annotator_id = make_annotator(client)
    task_id = make_task(client)

    submission = submit(client, task_id, annotator_id).json()
    assert submission["status"] == "submitted"
    assert submission["attempt"] == 1

    assert review(client, submission["id"], "accepted", 95).status_code == 201
    assert client.get(f"/submissions/{submission['id']}").json()["status"] == "accepted"


def test_submission_cannot_be_reviewed_twice(client):
    annotator_id = make_annotator(client)
    submission = submit(client, make_task(client), annotator_id).json()

    assert review(client, submission["id"], "accepted").status_code == 201
    assert review(client, submission["id"], "rejected").status_code == 409


def test_cannot_resubmit_without_rework(client):
    annotator_id = make_annotator(client)
    task_id = make_task(client)

    assert submit(client, task_id, annotator_id).status_code == 201
    # first submission is still pending review
    assert submit(client, task_id, annotator_id).status_code == 409


def test_rework_allows_a_second_attempt(client):
    annotator_id = make_annotator(client)
    task_id = make_task(client)

    first = submit(client, task_id, annotator_id).json()
    review(client, first["id"], "rework", 50)

    second = submit(client, task_id, annotator_id, content="negative").json()
    assert second["attempt"] == 2

    review(client, second["id"], "accepted", 90)
    metrics = client.get(f"/annotators/{annotator_id}/metrics").json()
    assert metrics["submissions"] == 2
    assert metrics["accepted"] == 1
    assert metrics["rework"] == 1


def test_annotator_metrics(client):
    annotator_id = make_annotator(client)

    for decision, score in [("accepted", 90), ("accepted", 70), ("rework", 50), ("rejected", 10)]:
        submission = submit(client, make_task(client), annotator_id).json()
        review(client, submission["id"], decision, score)

    metrics = client.get(f"/annotators/{annotator_id}/metrics").json()
    assert metrics == {
        "submissions": 4,
        "reviewed": 4,
        "accepted": 2,
        "rework": 1,
        "rejected": 1,
        "pending": 0,
        "approval_rate": 50.0,
        "rework_rate": 25.0,
        "average_score": 55.0,
    }


def test_metrics_for_annotator_without_reviews(client):
    annotator_id = make_annotator(client)
    metrics = client.get(f"/annotators/{annotator_id}/metrics").json()
    assert metrics["submissions"] == 0
    assert metrics["approval_rate"] == 0.0
    assert metrics["average_score"] is None


def test_project_metrics_aggregate_all_annotators(client):
    alice = make_annotator(client, "alice")
    bob = make_annotator(client, "bob")
    task_a = make_task(client, project="alpha")
    task_b = make_task(client, project="alpha")
    task_c = make_task(client, project="alpha")
    other_project_task = make_task(client, project="beta")

    review(client, submit(client, task_a, alice).json()["id"], "accepted", 100)
    review(client, submit(client, task_b, bob).json()["id"], "rework", 60)
    submit(client, task_c, bob)  # still pending
    review(client, submit(client, other_project_task, alice).json()["id"], "rejected", 0)

    metrics = client.get("/projects/alpha/metrics").json()
    assert metrics["submissions"] == 3
    assert metrics["reviewed"] == 2
    assert metrics["pending"] == 1
    assert metrics["approval_rate"] == 50.0
    assert metrics["rework_rate"] == 50.0
    assert metrics["average_score"] == 80.0


def test_review_validation(client):
    annotator_id = make_annotator(client)
    submission = submit(client, make_task(client), annotator_id).json()

    too_high = client.post(
        f"/submissions/{submission['id']}/review",
        json={"reviewer": "reviewer1", "decision": "accepted", "score": 150},
    )
    assert too_high.status_code == 422

    bad_decision = client.post(
        f"/submissions/{submission['id']}/review",
        json={"reviewer": "reviewer1", "decision": "maybe", "score": 50},
    )
    assert bad_decision.status_code == 422
