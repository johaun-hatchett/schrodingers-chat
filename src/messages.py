"""Defines the message types and transcript for the game."""
from typing import Dict, List, Iterator, Optional, Union


class BaseMessage:
    def __init__(self, speaker: str, content: str) -> None:
        self.speaker = speaker
        self.content = content
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(speaker={self.speaker}, content={repr(self.content)})"
    
    def __str__(self) -> str:
        return self.content

    def serialize(self) -> Dict[str, str]:
        return {"speaker": self.speaker, "content": self.content}


class HumanMessage(BaseMessage):
    def __init__(self, content: str) -> None:
        super().__init__(speaker="human", content=content)

    @classmethod
    def create_from_prompt(cls) -> "HumanMessage":
        content = input("> ")
        return cls(content)


class AIMessage(BaseMessage):
    def __init__(self, content: str) -> None:
        super().__init__(speaker="ai", content=content)
    

MessageType = Union[HumanMessage, AIMessage]


class Transcript:
    def __init__(self, messages: Optional[List[MessageType]]=None) -> None:
        self.messages = messages if messages is not None else []

    def __iter__(self) -> Iterator[MessageType]:
        return iter(self.messages)
    
    def add(self, message: MessageType) -> None:
        self.messages.append(message)

    def serialize(self) -> List[Dict[str, str]]:
        return [message.serialize() for message in self.messages]


def message_from_dict(entry: dict) -> BaseMessage:
    """Convert a serialized message dict back into a message object."""
    speaker = entry.get("speaker", "")
    content = entry.get("content", "")

    if speaker == "human":
        return HumanMessage(content)
    if speaker == "ai":
        return AIMessage(content)
    # Fallback – preserve unknown speakers
    return BaseMessage(speaker=speaker or "unknown", content=content)