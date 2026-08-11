import httpx
import pytest


def _provider_module():
    from app.providers import chat

    return chat


def test_glm_provider_sends_json_mode_and_returns_parsed_object():
    chat = _provider_module()
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers.get("authorization")
        captured["json"] = __import__("json").loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": '{"issues": [{"explanation": "测试"}]}'}}
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = chat.OpenAICompatibleChatProvider(
        api_base_url="https://open.bigmodel.cn/api/paas/v4",
        api_key="test-secret",
        model="glm-4.7",
        timeout_seconds=5,
        thinking_enabled=True,
        client=client,
    )

    result = provider.complete(
        [{"role": "user", "content": "审查第三条"}],
        response_format={"type": "json_object"},
    )

    assert result == {"issues": [{"explanation": "测试"}]}
    assert captured["authorization"] == "Bearer test-secret"
    assert captured["json"]["model"] == "glm-4.7"
    assert captured["json"]["response_format"] == {"type": "json_object"}
    assert captured["json"]["thinking"] == {"type": "enabled"}
    assert captured["json"]["stream"] is False


def test_glm_provider_rejects_missing_key_before_network_request():
    chat = _provider_module()
    provider = chat.OpenAICompatibleChatProvider(
        api_base_url="https://open.bigmodel.cn/api/paas/v4",
        api_key="",
        model="glm-4.7",
    )

    with pytest.raises(chat.ChatProviderConfigurationError, match="API Key"):
        provider.complete([{"role": "user", "content": "test"}])


def test_glm_provider_explicitly_disables_thinking_for_fast_review_mode():
    chat = _provider_module()
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["json"] = __import__("json").loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"issues": []}'}}]},
        )

    provider = chat.OpenAICompatibleChatProvider(
        api_base_url="https://open.bigmodel.cn/api/paas/v4",
        api_key="test-secret",
        model="glm-4.7",
        thinking_enabled=False,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    provider.complete([{"role": "user", "content": "审查第三条"}])

    assert captured["json"]["thinking"] == {"type": "disabled"}


@pytest.mark.parametrize("status", [401, 403])
def test_glm_provider_reports_authentication_failure_without_leaking_key(status):
    chat = _provider_module()

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": {"message": "invalid key test-secret"}})

    provider = chat.OpenAICompatibleChatProvider(
        api_base_url="https://open.bigmodel.cn/api/paas/v4",
        api_key="test-secret",
        model="glm-4.7",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(chat.ChatProviderAuthenticationError) as exc:
        provider.complete([{"role": "user", "content": "test"}])

    assert "test-secret" not in str(exc.value)


def test_glm_provider_rejects_malformed_model_json():
    chat = _provider_module()

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "not-json"}}]})

    provider = chat.OpenAICompatibleChatProvider(
        api_base_url="https://open.bigmodel.cn/api/paas/v4",
        api_key="test-secret",
        model="glm-4.7",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(chat.ChatProviderResponseError, match="JSON"):
        provider.complete([{"role": "user", "content": "test"}])
