"""Anthropic tool-use adapter. No dependency on the ``anthropic`` package."""

from __future__ import annotations

import json
from typing import Any, Optional

from .._client import OpenType
from ._definitions import TOOLS, ToolSet, attr


class AnthropicTools(ToolSet):
    def handle_tool_use(self, block: Any) -> dict[str, Any]:
        """Take a ``tool_use`` content block (object or dict) and return the
        ``tool_result`` block to send back."""
        content = self.handle(attr(block, "name"), attr(block, "input"))
        result: dict[str, Any] = {"type": "tool_result", "tool_use_id": attr(block, "id"), "content": content}
        if content.startswith('{"error"'):
            result["is_error"] = True
        return result


def anthropic_tools(client: Optional[OpenType] = None) -> AnthropicTools:
    defs = [
        {"name": t.name, "description": t.description, "input_schema": json.loads(json.dumps(t.input_schema))}
        for t in TOOLS
    ]
    return AnthropicTools(client, defs)
