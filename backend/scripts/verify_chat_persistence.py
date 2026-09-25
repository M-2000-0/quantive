"""Live verification: AI chat conversation persistence.

Flow:
  1. Login as demo user (cookie + CSRF dance).
  2. POST /api/ai/chat twice — assert conversation_id returned and thread
     created with 2 messages.
  3. GET /api/ai/conversations — thread listed.
  4. GET /api/ai/conversations/{id} — both turns present, sources persisted.
  5. Cross-user isolation: patricio@quantive.com must NOT see the thread.
  6. DELETE /api/ai/conversations/{id} — thread gone.
"""
import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"


def get_csrf():
    req = urllib.request.Request(f"{BASE}/api/health")
    with urllib.request.urlopen(req, timeout=30) as r:
        set_cookie = r.headers.get("Set-Cookie", "")
        for part in set_cookie.split(";"):
            part = part.strip()
            if part.startswith("csrf_token="):
                return part.split("=", 1)[1]
    return ""


def opener():
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor())


def login(op, email, password):
    csrf = get_csrf()
    req = urllib.request.Request(
        f"{BASE}/api/auth/login",
        data=json.dumps({"email": email, "password": password}).encode(),
        headers={"Content-Type": "application/json", "X-CSRF-Token": csrf},
        method="POST",
    )
    with op.open(req, timeout=30) as r:
        body = json.loads(r.read())
        assert body.get("user", {}).get("email") == email, f"login failed for {email}"
    return csrf


def post(op, path, payload, csrf):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "X-CSRF-Token": csrf},
        method="POST",
    )
    with op.open(req, timeout=300) as r:
        return json.loads(r.read())


def req(op, path, method="GET", csrf=None):
    headers = {"X-CSRF-Token": csrf} if csrf else {}
    r = urllib.request.Request(f"{BASE}{path}", headers=headers, method=method)
    with op.open(r, timeout=60) as resp:
        return json.loads(resp.read())


def get_status(op, path):
    try:
        req(op, path)
        return 200
    except urllib.error.HTTPError as e:
        return e.code


def main():
    ok = True

    # ── demo user flow ──
    op = opener()
    csrf = login(op, "demo_stress@test.com", "DemoPass123!")

    print("[1] first chat turn…")
    r1 = post(op, "/api/ai/chat", {"message": "What happens to my debt if rates rise 50bps?", "max_new_tokens": 40}, csrf)
    conv_id = r1.get("conversation_id")
    assert conv_id, f"FAIL: no conversation_id in response: {list(r1.keys())}"
    print(f"    conversation_id={conv_id}")

    print("[2] second chat turn (same thread)…")
    r2 = post(op, "/api/ai/chat", {"message": "what about 100bps?", "max_new_tokens": 40, "conversation_id": conv_id}, csrf)
    assert r2.get("conversation_id") == conv_id, "FAIL: second turn created a different thread"
    print("    same thread confirmed")

    print("[3] GET /api/ai/conversations lists the thread…")
    lst = req(op, "/api/ai/conversations")
    convs = [c for c in lst["conversations"] if c["id"] == conv_id]
    assert convs, "FAIL: thread missing from list"
    assert convs[0]["message_count"] == 4, f"FAIL: expected 4 messages (2 exchanges), got {convs[0]['message_count']}"
    assert "rates rise 50bps" in convs[0]["title"].lower() or "50bps" in convs[0]["title"].lower(), \
        f"FAIL: title not derived from first question: {convs[0]['title']}"
    print(f"    title={convs[0]['title']!r}, messages={convs[0]['message_count']}")

    print("[4] GET /api/ai/conversations/{id} restores turns…")
    conv = req(op, f"/api/ai/conversations/{conv_id}")
    msgs = conv["messages"]
    assert len(msgs) == 4, f"FAIL: expected 4 messages, got {len(msgs)}"
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"], \
        f"FAIL: unexpected role order: {[m['role'] for m in msgs]}"
    assert msgs[0]["role"] == "user" and "50bps" in msgs[0]["content"]
    assert msgs[1]["role"] == "assistant" and msgs[1]["content"]
    assert "100bps" in msgs[2]["content"], f"FAIL: second user turn missing: {msgs[2]['content']}"
    print(f"    roles={[m['role'] for m in msgs]}, assistant chars={[len(m['content']) for m in msgs if m['role']=='assistant']}")

    print("[5] cross-user isolation…")
    op2 = opener()
    csrf2 = login(op2, "patricio@quantive.com", "QuantumComp")
    lst2 = req(op2, "/api/ai/conversations")
    assert not any(c["id"] == conv_id for c in lst2["conversations"]), "FAIL: thread leaked to other user"
    status = get_status(op2, f"/api/ai/conversations/{conv_id}")
    assert status == 404, f"FAIL: other user direct GET returned {status}, expected 404"
    print("    other user: not listed, direct GET → 404 ✓")

    print("[6] DELETE /api/ai/conversations/{id}…")
    d = req(op, f"/api/ai/conversations/{conv_id}", method="DELETE", csrf=csrf)
    assert d.get("deleted") == conv_id
    lst3 = req(op, "/api/ai/conversations")
    assert not any(c["id"] == conv_id for c in lst3["conversations"]), "FAIL: thread still listed after delete"
    print("    deleted ✓")

    print("\nALL PERSISTENCE CHECKS PASSED" if ok else "\nFAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
