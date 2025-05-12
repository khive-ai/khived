# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel

from khive.connections.endpoint import Endpoint, EndpointConfig
from khive.utils import is_package_installed

_HAS_OLLAMA = is_package_installed("ollama")

OLLAMA_CHAT_ENDPOINT_CONFIG = EndpointConfig(
    name="ollama_chat",
    provider="ollama",
    base_url="http://localhost:11434/v1",
    endpoint="chat",
    kwargs={"model": ""},
    openai_compatible=True,
    api_key="OLLAMA",
    transport_type="sdk",
)


class OllamaChatEndpoint(Endpoint):
    """
    Documentation: https://platform.openai.com/docs/api-reference/chat/create
    """

    def __init__(self, config=OLLAMA_CHAT_ENDPOINT_CONFIG, **kwargs):
        if not _HAS_OLLAMA:
            raise ModuleNotFoundError(
                "ollama is not installed, please install it with `pip install khive[ollama]`"
            )
        super().__init__(config, **kwargs)

        from ollama import list as ollama_list  # type: ignore[import]
        from ollama import pull as ollama_pull  # type: ignore[import]

        super().__init__(config)
        self._pull = ollama_pull
        self._list = ollama_list

    async def call(
        self, request: dict | BaseModel, cache_control: bool = False, **kwargs
    ):
        payload, headers = self.create_payload(request, **kwargs)
        self._check_model(payload["model"])
        return await super().call(
            payload, cache_control=cache_control, headers=headers, **kwargs
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

    def _check_model(self, model: str):
        if model not in [i.model for i in self._list().models]:
            self._pull_model(model)
