from __future__ import annotations

import httpx
import pytest
import respx

from server.clients import EmbeddingClient, EndpointCapabilityError, HarnessClient


@respx.mock
def test_embedding_uses_openai_compatible_endpoint():
    route = respx.post("https://model.test/v1/embeddings").mock(
        return_value=httpx.Response(200, json={"data": [{"embedding": [0.2, 0.4]}]}))
    assert EmbeddingClient("https://model.test/v1", "secret")("orbit") == [0.2, 0.4]
    assert route.calls[0].request.headers["authorization"] == "Bearer secret"


@respx.mock
def test_embedding_reports_unsupported_endpoint():
    respx.post("https://model.test/v1/embeddings").mock(return_value=httpx.Response(404))
    with pytest.raises(EndpointCapabilityError, match="does not support embeddings"):
        EmbeddingClient("https://model.test/v1", "secret")("orbit")


@respx.mock
def test_harness_parses_fenced_json_and_attaches_trace_metadata():
    respx.post("http://harness.test/sessions").mock(
        return_value=httpx.Response(200, json={"id": "session-1"}))
    respx.post("http://harness.test/sessions/session-1/turns").mock(
        return_value=httpx.Response(200, json={"id": "turn-1", "status": "completed",
                                               "result_text": "```json\n{\"answer\": 42}\n```",
                                               "usage": {"prompt_tokens": 3}}))
    value = HarnessClient("http://harness.test").json("role", "instruction", {"question": "why"})
    assert value == {"answer": 42, "_session_id": "session-1", "_turn_id": "turn-1",
                     "_usage": {"prompt_tokens": 3}}
