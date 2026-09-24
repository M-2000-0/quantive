"""Demo-readiness stress test for Quantive AI (LLM + RAG + chat).

Logs in as a real user, exercises every AI-facing endpoint with realistic
prompts, and grades each response for demo viability. Run with servers up.
"""
import json
import re
import sys
import time
import urllib.request
import urllib.error
import http.cookiejar

BASE = "http://127.0.0.1:8000"
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def csrf():
    for c in jar:
        if c.name == "csrf_token":
            return c.value
    return ""


def req(method, path, body=None, timeout=120):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method)
    if body is not None:
        r.add_header("Content-Type", "application/json")
    tok = csrf()
    if tok:
        r.add_header("X-CSRF-Token", tok)
    try:
        with opener.open(r, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def grade(text):
    """Grade LLM output coherence for demo viability."""
    if not text or not text.strip():
        return 0
    words = text.split()
    if len(words) < 5:
        return 20
    # Real sentences: >60% alpha words, low punctuation-fragment ratio
    alpha = sum(1 for w in words if re.search(r"[a-zA-Z]{2,}", w))
    frags = sum(1 for w in words if re.fullmatch(r"[,.;:]+", w))
    if alpha / len(words) > 0.85 and frags / len(words) < 0.1:
        return 85
    if alpha / len(words) > 0.6:
        return 50
    return 15


def main():
    results = []

    # 0. Fresh login
    s, _ = req("POST", "/api/auth/register", {
        "email": "demo_stress@test.com", "password": "DemoPass123!", "name": "Demo Stress"})
    if s not in (200, 400):  # 400 = already exists, fine
        print(f"register status {s}")
    s, _ = req("POST", "/api/auth/login", {
        "email": "demo_stress@test.com", "password": "DemoPass123!"})
    print(f"login: {s}")

    # 1. Model status
    s, body = req("GET", "/api/ai/models")
    results.append(("model status", s, f"loaded={body.get('model_loaded')} params={body.get('parameters_m')}M", "-"))
    print(f"model status: {s} {body}")

    # 2. Generate — domain prompts a stakeholder would ask in a demo
    demo_prompts = [
        "What is sovereign debt optimization?",
        "Explain debt sustainability analysis",
        "How do bond auctions work?",
    ]
    for p in demo_prompts:
        t0 = time.time()
        s, body = req("POST", "/api/ai/generate", {"prompt": p, "max_new_tokens": 80})
        text = (body.get("text") or "") if isinstance(body, dict) else ""
        results.append((f"generate: {p[:40]}", s, f"{len(text)} chars, {time.time()-t0:.1f}s",
                        f"grade={grade(text)}"))
        print(f"\n>>> {p}\n    status={s} grade={grade(text)}\n    {text[:200]!r}")

    # 3. RAG chat — the grounded path
    for q in demo_prompts[:2]:
        t0 = time.time()
        s, body = req("POST", "/api/ai/chat", {"message": q, "max_new_tokens": 120})
        text = (body.get("text") or "") if isinstance(body, dict) else ""
        srcs = body.get("sources") or []
        results.append((f"rag chat: {q[:40]}", s,
                        f"sources={len(srcs)}, {time.time()-t0:.1f}s", f"grade={grade(text)}"))
        print(f"\n>>> RAG {q}\n    status={s} sources={len(srcs)} grade={grade(text)}\n    {text[:200]!r}")

    # 4. Product chat assistant (rule-based)
    s, body = req("POST", "/api/chat", {"message": "What are my balances?"})
    text = (body.get("content") or "") if isinstance(body, dict) else ""
    results.append(("product chat: balances", s, f"{len(text)} chars", f"grade={grade(text)}"))
    print(f"\n>>> product chat\n    status={s}\n    {text[:200]!r}")

    # 5. Personal intelligence (user-facing ask)
    s, body = req("POST", "/api/personal/intelligence/ask", {"question": "What deductions can I claim?"})
    ok = s == 200 and isinstance(body, dict) and body.get("answer")
    results.append(("personal intelligence ask", s, json.dumps(body)[:120] if not ok else "answered", 85 if ok else 0))
    print(f"\n>>> personal ask: status={s} {json.dumps(body)[:200]}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for name, s, info, g in results:
        print(f"{g:>4}  {s:>4}  {name:45}  {info}")
    grades = [int(g.split("=")[1]) for _, _, _, g in results if g.startswith("grade=")]
    grades += [g for _, _, _, g in results if isinstance(g, int)]
    if grades:
        print(f"\nAverage demo grade: {sum(grades)/len(grades):.0f}/100  ({len(grades)} graded calls)")


if __name__ == "__main__":
    sys.exit(main())
