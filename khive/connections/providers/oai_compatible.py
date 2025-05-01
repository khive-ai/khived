from pydantic import BaseModel

from khive.config import settings
from khive.connections.endpoint import Endpoint, EndpointConfig

try:
    from khive.third_party.openai_models import (  # type: ignore[import]
        CreateChatCompletionRequest,
        CreateResponse,
    )
except ModuleNotFoundError:
    raise RuntimeError("Generate OpenAI models first – see khive/third_party/README.md")

_HAS_OLLAMA = True
try:
    import ollama  # type: ignore
except ImportError:
    _HAS_OLLAMA = False


__all__ = (
    "OllamaChatEndpoint",
    "OpenaiChatEndpoint",
    "OpenaiResponseEndpoint",
    "OpenrouterChatEndpoint",
)

OPENAI_CHAT_ENDPOINT_CONFIG = EndpointConfig(
    name="openai_chat",
    provider="openai",
    base_url=None,
    endpoint="chat/completions",
    kwargs={"model": "gpt-4o"},
    openai_compatible=True,
    api_key=settings.OPENAI_API_KEY,
    auth_template={"Authorization": "Bearer $API_KEY"},
    default_headers={"content-type": "application/json"},
    request_options=CreateChatCompletionRequest,
)

OPENAI_RESPONSE_ENDPOINT_CONFIG = EndpointConfig(
    name="openai_response",
    provider="openai",
    base_url=None,
    endpoint="response",
    kwargs={"model": "gpt-4o"},
    openai_compatible=True,
    api_key=settings.OPENAI_API_KEY,
    auth_template={"Authorization": "Bearer $API_KEY"},
    default_headers={"content-type": "application/json"},
    request_options=CreateResponse,
)

OPENROUTER_CHAT_ENDPOINT_CONFIG = EndpointConfig(
    name="openrouter_chat",
    provider="openrouter",
    base_url="https://openrouter.ai/api/v1",
    endpoint="chat/completions",
    kwargs={"model": "gpt-4o"},
    openai_compatible=True,
    api_key=settings.OPENROUTER_API_KEY,  # Use SecretStr from settings
    auth_template={"Authorization": "Bearer $API_KEY"},
    default_headers={"content-type": "application/json"},
    request_options=CreateChatCompletionRequest,
)


class OpenaiChatEndpoint(Endpoint):
    def __init__(self, config=OPENAI_CHAT_ENDPOINT_CONFIG, **kwargs):
        super().__init__(config, **kwargs)


class OpenaiResponseEndpoint(Endpoint):
    def __init__(self, config=OPENAI_RESPONSE_ENDPOINT_CONFIG, **kwargs):
        super().__init__(config, **kwargs)


class OpenrouterChatEndpoint(Endpoint):
    def __init__(self, config=OPENROUTER_CHAT_ENDPOINT_CONFIG, **kwargs):
        super().__init__(config, **kwargs)


# Ollama runs locally with no auth, but we need a placeholder key for the interface
DUMMY_OLLAMA_API_KEY = "no_key_required"

ENDPOINT_CONFIG = EndpointConfig(
    name="ollama_chat",
    provider="ollama",
    base_url="http://localhost:11434/v1",
    endpoint="chat",
    kwargs={"model": "qwen3"},
    openai_compatible=True,
    api_key=settings.OLLAMA_API_KEY or DUMMY_OLLAMA_API_KEY,  # Use dummy key if not set
    auth_template={"Authorization": "Bearer $API_KEY"},
    default_headers={"content-type": "application/json"},
    request_options=CreateChatCompletionRequest,
)


class OllamaChatEndpoint(Endpoint):
    """
    Documentation: https://github.com/ollama/ollama/tree/main/docs
    """

    def __init__(self, config=ENDPOINT_CONFIG, **kwargs):
        if not _HAS_OLLAMA:
            raise ImportError(
                "Package `ollama` is required to use the ollama chat endpoint. Please install it via `pip install ollama` and make sure the desktop client is running, to use this feature."
            )

        super().__init__(config, **kwargs)

        # Warn if a real key was provided (Ollama doesn't need authentication)
        if self.config.api_key and self.config._api_key != DUMMY_OLLAMA_API_KEY:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                "Ollama runs unauthenticated locally; supplied API key will be ignored."
            )

        from ollama import list as o_list  # type: ignore
        from ollama import pull as o_pull  # type: ignore

        self._pull = o_pull
        self._list = o_list

    @property
    def allowed_roles(self):
        return ["system", "user", "assistant"]

    async def call(
        self, request: dict | BaseModel, cache_control: bool = False, **kwargs
    ):
        payload, _ = self.create_payload(request, **kwargs)
        self._check_model(payload.get("model"))

        return await super().call(
            request=request, cache_control=cache_control, **kwargs
        )

    def _pull_model(self, model: str):
        from tqdm import tqdm

        current_digest, bars = "", {}
        for progress in self._pull(model, stream=True):
            digest = progress.get("digest", "")
            if digest != current_digest and current_digest in bars:
                bars[current_digest].close()

            if not digest:
                print(progress.get("status"))
                continue

            if digest not in bars and (total := progress.get("total")):
                bars[digest] = tqdm(
                    total=total,
                    desc=f"pulling {digest[7:19]}",
                    unit="B",
                    unit_scale=True,
                )

            if completed := progress.get("completed"):
                bars[digest].update(completed - bars[digest].n)

            current_digest = digest

    def _list_local_models(self) -> set:
        response = self._list()
        return {i.model for i in response.models}

    def _check_model(self, model: str):
        if model not in self._list_local_models():
            self._pull_model(model)
