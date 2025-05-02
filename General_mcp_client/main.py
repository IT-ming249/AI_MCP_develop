# 通用客户端开发思路
# 1. 读取本客户端支持的所有Client
# 2. 连接所有的Mcp Server 获取所有Mcp Server 的Tool Promote Resource
# 3. 调用大模型，让大模型自由选择函数(Tool/Promote/Resource)
# 4. 其它操作 eg:读取用户输入，MCP与大模型交互等
import asyncio
from typing import Any
from server import MCPServer, MCPServerManager
from contextlib import AsyncExitStack
from openai import OpenAI
from mcp.shared.exceptions import McpError
import json
import model_config

class MCPMain:
    def __init__(self):
        self.manager: MCPServerManager|None = None
        self._exit_stack = AsyncExitStack()
        self._llm:OpenAI | None = None
        self.calling_functions: list[dict[str, Any]] = []

    async def initialize(self):
        with open("./mcp.json", "r",encoding="utf-8") as fp:
            content = fp.read()
        mcp_config = json.loads(content)
        mcp_dict = mcp_config["mcpServers"]
        manager = MCPServerManager(mcp_dict)
        self.manager = await self._exit_stack.enter_async_context(manager)
        for name, function in manager.all_functions.items():
            self.calling_functions.append({
                "type":"function",
                "function":{
                    "name":name,
                    "description":function.description,
                    "input_schema":function.input_schema,
                }
            })
    async def run(self):
        # 不断读取用书的输入，并与MCP以及大模型进行互动
        messages = []
        self._llm = self.llm
        while True:
            query = input("请输入")
            if query == "exit":
                break
            messages.append({
                "role":"user",
                "content":query
            })
            #用户输入的query可能需要调用多次大模型才能输出结果，调用大模型也要在循环中
            while True:
                response = self._llm.chat.completions.create(
                    messages=messages,
                    model=model_config.LLM_MODEL,
                    tools=self.calling_functions,
                )
                choice = response.choices[0]
                if choice.finish_reason == "stop":
                    message = choice.message
                    content = message.content
                    print(f"AI回复{content}")
                    break
                elif choice.finish_reason == "tool_calls":
                    messages.append(choice.message.model_dump())
                    tool_calls = choice.message.tool_calls
                    for tool_call in tool_calls:
                        tool_call_id = tool_call.id
                        function = tool_call.function
                        function_name = function.name
                        function_arguments = json.loads(function.arguments)
                        try:
                            function_ex_result = await self.manager.call_functions(
                                name=function_name,
                                arguments=function_arguments,
                            )
                        except McpError as e:
                            messages.append({
                                "role": "tool",
                                "content": f"执行出现异常{str(e)}",
                                "tool_call_id": tool_call_id,
                            })
                        else:
                            messages.append({
                                "role": "tool",
                                "content": function_ex_result,
                                "tool_call_id": tool_call_id,
                            })
                        print(f"AI执行了{function_name}")

    @property
    def llm(self):
        if self._llm is None:
            self._llm = OpenAI(
                api_key=model_config.LLM_API_KEY,
                base_url=model_config.LLM_API_BASE_URL
            )
        return self._llm

    async def aclose(self):
        await self._exit_stack.aclose()

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()

async def main():
    async with MCPMain() as app:
        await app.run()

if __name__ == "__main__":
    #asyncio.run(main())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())