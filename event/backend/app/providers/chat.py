import json
from collections.abc import Generator
from typing import Any, Protocol

import httpx

from ..config import get_settings


class ChatProviderError(RuntimeError):
    """Safe, user-displayable provider error."""


class ChatProviderConfigurationError(ChatProviderError):
    pass


class ChatProviderAuthenticationError(ChatProviderError):
    pass


class ChatProviderTimeoutError(ChatProviderError):
    pass


class ChatProviderResponseError(ChatProviderError):
    pass


class ChatModelProvider(Protocol):
    def complete(
        self,
        messages: list[dict[str, str]],
        response_format: dict[str, str] | None = None,
    ) -> dict[str, Any]: ...


class OpenAICompatibleChatProvider:
    """Chat-completions adapter used by GLM-4.7 and compatible domestic providers."""

    def __init__(
        self,
        *,
        api_base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 120,
        thinking_enabled: bool = True,
        max_tokens: int = 8192,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key.strip()
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.thinking_enabled = thinking_enabled
        self.max_tokens = max_tokens
        self.client = client or httpx.Client(timeout=timeout_seconds)

    def complete(
        self,
        messages: list[dict[str, str]],
        response_format: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise ChatProviderConfigurationError("尚未配置 GLM API Key")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": 0.1,
            "max_tokens": self.max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format
        if self.thinking_enabled:
            payload["thinking"] = {"type": "enabled"}

        try:
            response = self.client.post(
                f"{self.api_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=self.timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise ChatProviderTimeoutError("GLM 响应超时，请稍后重试") from exc
        except httpx.HTTPError as exc:
            raise ChatProviderError("无法连接 GLM 服务，请检查网络") from exc

        if response.status_code in (401, 403):
            raise ChatProviderAuthenticationError("GLM API Key 无效或无权使用当前模型")
        if response.status_code >= 400:
            raise ChatProviderError(f"GLM 服务暂时不可用（HTTP {response.status_code}）")

        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            result = json.loads(content)
        except (ValueError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ChatProviderResponseError("GLM 未返回有效 JSON 结果") from exc

        if not isinstance(result, dict):
            raise ChatProviderResponseError("GLM 返回的 JSON 顶层必须是对象")
        return result

    def close(self) -> None:
        self.client.close()


def get_chat_provider() -> Generator[OpenAICompatibleChatProvider, None, None]:
    settings = get_settings()
    provider = OpenAICompatibleChatProvider(
        api_base_url=settings.llm_api_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_chat_model,
        timeout_seconds=settings.llm_timeout_seconds,
        thinking_enabled=settings.llm_thinking_enabled,
        max_tokens=settings.llm_max_tokens,
    )
    try:
        yield provider
    finally:
        provider.close()
