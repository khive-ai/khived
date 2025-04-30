from typing import Any, Literal
from uuid import UUID

from pydantic import Field, field_serializer, field_validator

from khive.protocols.element import Element, Log
from khive.protocols.node import Node
from khive.protocols.pile import Pile
from khive.services.endpoint import APICalling, Endpoint, EndpointConfig, iModel


class Message(Node):

    sender: UUID | str | None = None
    recepient: UUID | str | None = None
    role: Literal["developer", "user", "assistant", "system"] = "user"

    @field_validator("sender", "recepient", mode="before")
    def _validate_sender_recepient(cls, value: UUID | str) -> UUID:
        return cls._validate_id(value)

    @property
    def chat_msg(self) -> dict:
        return {"role": self.role, "content": self.content}


class Branch(Element):

    user: UUID | str | None = Field(
        None,
        description=(
            "The user or sender of the branch, often a session object or "
            "an external user identifier. Not to be confused with the "
            "LLM API's user parameter."
        ),
    )
    name: str | None = Field(
        None,
        description=(
            "The name of the branch, which can be used to identify it "
            "within a session or conversation."
        ),
    )
    messages: Pile[Message] = Field(
        default_factory=list,
        description=(
            "A list of messages exchanged in the branch, typically "
            "between the user and the assistant."
        ),
    )
    system: Message | None = Field(
        None,
        description=(
            "A system message that can be used to set the context or "
            "instructions for the assistant."
        ),
    )
    logs: Pile[Log] = Field(default_factory=Pile)
    services: dict[str, iModel] = Field(default_factory=dict)

    def connect(
        self,
        endpoint: Endpoint | EndpointConfig | dict,
        name: str | None = None,
        request_limit: int | None = 100,
        concurrency_limit: int | None = 20,
        limit_interval: int | None = 60,
        **kwargs,
    ):
        imodel = iModel(
            endpoint=endpoint,
            name=name,
            request_limit=request_limit,
            concurrency_limit=concurrency_limit,
            limit_interval=limit_interval,
            **kwargs,
        )
        if imodel.name in self.services:
            raise ValueError(f"Service {imodel.name} already exists in the branch.")
        self.services[imodel.name] = imodel

    @property
    def chat_model(self):
        return self.services.get("chat")

    async def query(
        self,
        content: Any,
        imodel: str | iModel | None = None,
        input_key: str = "messages",
        **kwargs,
    ):
        if isinstance(imodel, str):
            if not imodel in self.services:
                raise ValueError(f"Service {imodel} not found in the branch.")
            imodel = self.services[imodel]
        if isinstance(imodel, iModel):
            if not imodel.name in self.services:
                raise ValueError(f"Service {imodel.name} not found in the branch.")
        imodel = imodel or self.chat_model
        async with self.messages:
            user_msg = Message(
                sender=self.user,
                recepient=self.id,
                role="user",
                content=content,
            )
            self.messages.append(user_msg)

            if imodel.endpoint.config.endpoint == "responses":
                input_key = "input"
                if self.system:
                    kwargs[input_key] = [
                        {"role": "developer", "content": self.system.content}
                    ]
                else:
                    kwargs[input_key] = []
                kwargs[input_key].extend([i.chat_msg for i in self.messages])
            kwargs[input_key] = [i.chat_msg for i in self.messages]

        result: APICalling = await imodel.invoke(**kwargs)
        self.logs.append(Log.create(result))
        return result.response

    @field_serializer()
    def to_dict(self): ...
