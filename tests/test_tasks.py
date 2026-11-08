import pytest


def make(client, **kw):
    r = client.post("/tasks", json={"title": "t", **kw})
    assert r.status_code == 201, r.text
    return r.json()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_create_minimal_defaults(client):
    t = make(client, title="Buy milk")
    assert t["title"] == "Buy milk"
    assert (t["status"], t["priority"], t["description"], t["due_date"]) == ("pending", "medium", None, None)
    assert t["id"] and t["created_at"] and t["updated_at"]


def test_create_full_due_date_roundtrip(client):
    t = make(client, title="Report", description="Q3", status="in_progress", priority="high", due_date="2026-12-31")
    got = client.get(f"/tasks/{t['id']}").json()
    assert got["due_date"] == "2026-12-31"
    assert (got["description"], got["status"], got["priority"]) == ("Q3", "in_progress", "high")


@pytest.mark.parametrize("body", [
    {},
    {"title": ""},
    {"title": "x" * 201},
    {"title": "a", "status": "nope"},
    {"title": "a", "priority": "urgent"},
    {"title": "a", "due_date": "2026-13-40"},
    {"title": "a", "extra": 1},
])
def test_create_invalid(client, body):
    assert client.post("/tasks", json=body).status_code == 422


def test_get_by_id(client):
    t = make(client)
    assert client.get(f"/tasks/{t['id']}").json() == t
    assert client.get("/tasks/9999").status_code == 404


def test_list_total_and_order(client):
    ids = [make(client, title=f"t{i}")["id"] for i in range(3)]
    body = client.get("/tasks").json()
    assert body["total"] == 3
    assert [t["id"] for t in body["items"]] == ids[::-1]


def test_filters(client):
    make(client, status="done", priority="high")
    make(client, status="done", priority="low")
    make(client, status="pending", priority="high")
    assert client.get("/tasks", params={"status": "done"}).json()["total"] == 2
    assert client.get("/tasks", params={"priority": "high"}).json()["total"] == 2
    r = client.get("/tasks", params={"status": "done", "priority": "high"}).json()
    assert r["total"] == 1 and r["items"][0]["priority"] == "high"
    assert client.get("/tasks", params={"status": "bogus"}).status_code == 422


def test_search_case_insensitive_and_literal_percent(client):
    make(client, title="Fix LOGIN bug")
    make(client, title="100% coverage")
    make(client, title="100 tests")
    assert client.get("/tasks", params={"search": "login"}).json()["total"] == 1
    r = client.get("/tasks", params={"search": "0%"}).json()
    assert r["total"] == 1 and r["items"][0]["title"] == "100% coverage"


def test_pagination(client):
    for i in range(5):
        make(client, title=f"t{i}")
    pages = [client.get("/tasks", params={"limit": 2, "offset": o}).json() for o in (0, 2, 4)]
    assert [len(p["items"]) for p in pages] == [2, 2, 1]
    assert {p["total"] for p in pages} == {5}
    assert len({t["id"] for p in pages for t in p["items"]}) == 5
    assert pages[1]["limit"] == 2 and pages[1]["offset"] == 2


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_pagination_invalid(client, params):
    assert client.get("/tasks", params=params).status_code == 422


def test_patch_one_field_keeps_others(client):
    t = make(client, title="orig", description="d", priority="high")
    r = client.patch(f"/tasks/{t['id']}", json={"description": "new"})
    assert r.status_code == 200
    u = r.json()
    assert u["description"] == "new"
    assert (u["title"], u["priority"], u["status"]) == ("orig", "high", "pending")
    assert u["updated_at"] >= u["created_at"]


def test_patch_status_done(client):
    t = make(client)
    assert client.patch(f"/tasks/{t['id']}", json={"status": "done"}).json()["status"] == "done"
    assert client.get(f"/tasks/{t['id']}").json()["status"] == "done"


def test_patch_empty_returns_current(client):
    t = make(client)
    assert client.patch(f"/tasks/{t['id']}", json={}).json() == t


@pytest.mark.parametrize("body", [{"title": ""}, {"title": None}, {"status": None}, {"priority": None}])
def test_patch_invalid(client, body):
    t = make(client)
    assert client.patch(f"/tasks/{t['id']}", json=body).status_code == 422


def test_patch_missing(client):
    assert client.patch("/tasks/9999", json={"title": "x"}).status_code == 404


def test_delete(client):
    t = make(client)
    assert client.delete(f"/tasks/{t['id']}").status_code == 204
    assert client.get(f"/tasks/{t['id']}").status_code == 404
    assert client.delete(f"/tasks/{t['id']}").status_code == 404


@pytest.mark.parametrize("url", ["/tasks/9223372036854775808", "/tasks/0", "/tasks?offset=9223372036854775808"])
def test_integer_bounds(client, url):
    assert client.get(url).status_code == 422


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_id_overflow_patch_delete(client, method):
    kw = {"json": {"title": "x"}} if method == "patch" else {}
    assert getattr(client, method)("/tasks/9223372036854775808", **kw).status_code == 422


def test_title_whitespace(client):
    assert client.post("/tasks", json={"title": "   "}).status_code == 422
    t = make(client, title="  padded  ")
    assert t["title"] == "padded"
    assert client.patch(f"/tasks/{t['id']}", json={"title": "  "}).status_code == 422


@pytest.mark.parametrize("due", [0, 1730764800, 1.5])
def test_due_date_rejects_numbers(client, due):
    assert client.post("/tasks", json={"title": "a", "due_date": due}).status_code == 422
    t = make(client)
    assert client.patch(f"/tasks/{t['id']}", json={"due_date": due}).status_code == 422


def test_due_date_iso_string(client):
    assert make(client, due_date="2026-11-05")["due_date"] == "2026-11-05"


def test_description_max_length(client):
    assert client.post("/tasks", json={"title": "a", "description": "x" * 10_001}).status_code == 422
    assert make(client, description="x" * 10_000)["description"] == "x" * 10_000
