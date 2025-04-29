from openai import OpenAI
from mcp.client.sse import sse_client
from mcp import ClientSession
import asyncio
from contextlib import AsyncExitStack
from mcp.types import (LoggingMessageNotificationParams, ServerRequest, ClientResult, ServerNotification,
                       CreateMessageRequestParams, CreateMessageResult, TextContent)
from mcp.shared.context import RequestContext
from mcp.shared.session import RequestResponder
from typing import Any

# 使用ClientSession自带的回调函数
async def logging_handler(params: LoggingMessageNotificationParams):
    print("日志信息")
    print(params)

async def message_handler(message: RequestResponder[ServerRequest, ClientResult]
        | ServerNotification
        | Exception):
    print("进度反馈")
    print(message)

async def sampling_handler(context: RequestContext["ClientSession", Any],
        params: CreateMessageRequestParams,) -> CreateMessageResult:
    print(f"context: {context}")
    print(f"params: {params}")
    messages = [{
        "role":params.messages[0].role,
        "content":params.messages[0].content.text,
    }]
    deepseek = OpenAI(
        api_key="sk-6d067e4813ee48448f1f4770bef1bdb7",
        base_url="https://api.deepseek.com/")
    response = deepseek.chat.completions.create(
        messages=messages,
        model="deepseek-chat"
    )
    choice = response.choices[0]
    message = choice.message
    return CreateMessageResult(role="assistant",
                               content=TextContent(type="text",text=message.content),
                               model="deepseek-chat")


class MCPClient:
    def __init__(self):
        self.deepseek = OpenAI(
            api_key="sk-6d067e4813ee48448f1f4770bef1bdb7",
            base_url="https://api.deepseek.com/"
        )
        self.exit_stack = AsyncExitStack()
        self.prompts = {}

    async def run(self,query: str):
        # 1. 创建读写流通道 sse_client接收服务端url/sse
        read_stream, write_stream = await self.exit_stack.enter_async_context(sse_client("http://127.0.0.1:8000/sse"))

        # 2. 创建客户端与服务端进行通信的session对象
        session: ClientSession = await self.exit_stack.enter_async_context(ClientSession(read_stream,write_stream,
                                                                                         logging_callback=logging_handler,
                                                                                         message_handler=message_handler,
                                                                                         sampling_callback=sampling_handler))
        # 3. 初始化通信 (三步固定流程)
        await session.initialize()

        tools = (await session.list_tools()).tools
        for tool in tools:
            name = tool.name
            #respones = await session.call_tool(name=name, arguments={"files": ["a.txt", "b.txt"]})
            respones = await session.call_tool(name=name)
            print(respones)



    async def aclose(self):
        await self.exit_stack.aclose()

async def main():
    client = MCPClient()
    try:
        await client.run("你好")
    finally:
        await client.aclose()  # 对上下文操作统一进行清理工作,不管程序运行正常与否都要进行清理

if __name__ == '__main__':
    asyncio.run(main())