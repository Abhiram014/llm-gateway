from app.auth import hash_key

CHAT = {"model": "mock-1", "messages": [{"role": "user", "content": "Hi"}]}


def test_no_key_returns_401(client):
    response = client.post("/v1/chat/completions", json=CHAT)
    assert response.status_code == 401


def test_wrong_key_returns_401(client):
    response = client.post("/v1/chat/completions", json=CHAT,
                           headers={"Authorization": "Bearer gw-not-a-real-key"})
    assert response.status_code == 401


def test_valid_key_works(client, auth_headers):
    response = client.post("/v1/chat/completions", json=CHAT, headers=auth_headers)
    assert response.status_code == 200


def test_revoked_key_returns_401(client, api_key, db):
    db(lambda conn: conn.execute(
        "UPDATE api_keys SET revoked_at = now() WHERE key_hash = $1", hash_key(api_key)
    ))
    response = client.post("/v1/chat/completions", json=CHAT,
                           headers={"Authorization": f"Bearer {api_key}"})
    assert response.status_code == 401


def test_key_is_stored_hashed(api_key, db):
    row = db(lambda conn: conn.fetchrow(
        "SELECT key_hash FROM api_keys WHERE key_hash = $1", hash_key(api_key)
    ))
    assert row is not None
    assert row["key_hash"] != api_key   # the real key is never stored