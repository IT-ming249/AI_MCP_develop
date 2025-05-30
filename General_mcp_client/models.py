from pydantic import BaseModel
from enum import Enum
from typing import Any
from mcp.types import AnyUrl,PromptArgument

class MCPFunctionType(Enum):
    TOOL = "tool",
    RESOURCE = "resource",
    RESOURCE_TEMPLATE = "resource_template",
    PROMPT = "prompt",

class MCPFunction(BaseModel):
    name: str
    origin_name: str
    server_name: str
    description: str
    type_: MCPFunctionType
    input_schema: dict[str, Any] | None = None, #tool独有
    uri: str | AnyUrl | None = None, # Resource_template/Resource专有
    arguments: list[PromptArgument] | None = None, #prompt 独有