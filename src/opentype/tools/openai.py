"""OpenAI function-calling adapter. No dependency on the ``openai`` package."""

from __future__ import annotations

import json
from typing import Any, Optional

from .._client import OpenType
from ._definitions import TOOLS, ToolSet, attr


class OpenAITools(ToolSet):
    """``definitions``: Chat Completions tools. ``responses_definitions``: Responses API tools."""

    @property
    def responses_definitions(self) -> list[dict[str, Any]]:
        return [{"type": "function", **d["function"]} for d in self.definitions]

    def handle_tool_call(self, tool_call: Any) -> dict[str, Any]:
        """Take a Chat Completions ``tool_call`` (object or dict) and return the
        ``{"role": "tool", ...}`` message to append."""
        fn = attr(tool_call, "function")
        content = self.handle(attr(fn, "name"), attr(fn, "arguments"))
        return {"role": "tool", "tool_call_id": attr(tool_call, "id"), "content": content}


def openai_tools(client: Optional[OpenType] = None) -> OpenAITools:
    defs = [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": json.loads(json.dumps(t.input_schema)),
            },
        }
        for t in TOOLS
    ]
    return OpenAITools(client, defs)
