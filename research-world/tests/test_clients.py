from __future__ import annotations

import httpx
import pytest
import respx

from server.clients import EmbeddingClient, EndpointCapabilityError


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
