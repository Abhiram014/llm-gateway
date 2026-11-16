from app.auth import create_api_key

CHAT = {"model": "mock-1", "messages": [{"role": "user", "content": "Hi"}]}


def make_key(db, rpm_limit):
    key = db(lambda conn: create_api_key(conn, "ratelimit-test", rpm_limit))
    return {"Authorization": f"Bearer {key}"}


def test_blocks_after_limit(client, db):
    headers = make_key(db, rpm_limit=3)
    codes = [client.post("/v1/chat/completions", json=CHAT, headers=headers).status_code
             for _ in range(4)]
    assert codes == [200, 200, 200, 429]


def test_429_includes_retry_after(client, db):
    headers = make_key(db, rpm_limit=1)
    client.post("/v1/chat/completions", json=CHAT, headers=headers)
    response = client.post("/v1/chat/completions", json=CHAT, headers=headers)
    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0


def test_limits_are_per_key(client, db):
    key_a = make_key(db, rpm_limit=1)
    key_b = make_key(db, rpm_limit=1)
    client.post("/v1/chat/completions", json=CHAT, headers=key_a)   # A uses its only coin
    blocked = client.post("/v1/chat/completions", json=CHAT, headers=key_a)
    other = client.post("/v1/chat/completions", json=CHAT, headers=key_b)
    assert blocked.status_code == 429
    assert other.status_code == 200    # B has its own jar