import httpx

KEY = "gw-5kOOBc1Cwxh79RNKBLfa3n0H62l5bC7Mmn9mNhTH1ww"

for i in range(1, 9):
    r = httpx.post(
        "http://localhost:8000/v1/chat/completions",
        headers={"Authorization": f"Bearer {KEY}"},
        json={"model": "mock-1", "messages": [{"role": "user", "content": "hi"}]},
    )
    print(i, r.status_code, r.headers.get("Retry-After", ""))