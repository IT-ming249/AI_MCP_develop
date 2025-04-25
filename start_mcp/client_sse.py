from openai import OpenAI
from mcp.client.sse import sse_client
from mcp import ClientSession
import asyncio
import json
from contextlib import AsyncExitStack

#stdio: 在客户端中，启应该新的子进程来执行服务端的脚本代码


class MCPClient:
    def __init__(self,server_path):
        self.server_path = server_path
        self.deepseek = OpenAI(
            api_key="sk-6d067e4813ee48448f1f4770bef1bdb7",
            base_url="https://api.deepseek.com/"
        )
        self.exit_stack = AsyncExitStack()

    async def run(self,query: str):
        # 1. 创建读写流通道 sse_client接收服务端url/sse
        read_stream, write_stream = await self.exit_stack.enter_async_context(sse_client("http://127.0.0.1:8000/sse"))

        # 2. 创建客户端与服务端进行通信的session对象
        session= await self.exit_stack.enter_async_context(ClientSession(read_stream,write_stream))

        # 3. 初始化通信 (三步固定流程)
        await session.initialize()

        # 获取服务端的tools
        response = await session.list_tools()
        # print(response)
        # 将工具封装成function calling格式的对象
        tools_func = []
        for tool in response.tools:
            name = tool.name
            description = tool.description
            inputSchema = tool.inputSchema
            tools_func.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": description,
                        "inputSchema": inputSchema,
                    }
                })
        # 发送消息给大模型，让大模型自主先择调用哪个工具
        # role:
        # 1.user 用户给大模型发送的消息
        # 2.assistant 大模型给用户发送的消息
        # 3.system 给大模型的系统提示词
        # 4.tool 函数执行完后返回的信息
        messages = [
            {
                "role": "user",
                "content": query,
            }
        ]
        deepseek_response = self.deepseek.chat.completions.create(
            messages=messages,
            model="deepseek-chat",
            tools=tools_func
        )
        # print(deepseek_response)
        choice = deepseek_response.choices[0]
        if choice.finish_reason == "tool_calls":
            # 大模型选择了工具的情况
            # 为了后期，大模型能更加精准的恢复，把大模型选择的工具的message，添加到messages中
            messages.append(choice.message.model_dump())  # model_dump可以把message变成function calling格式
            # 获取工具
            tool_calls = choice.message.tool_calls
            # 依次调用工具
            for tool_call in tool_calls:
                tool_call_id = tool_call.id  # 这个参数调用工具的时候要用
                function = tool_call.function
                function_name = function.name
                function_arguments = json.loads(function.arguments)
                result = await session.call_tool(
                    name=function_name,
                    arguments=function_arguments,
                )
                content = result.content[0].text
                messages.append({
                    "role": "tool",
                    "content": content,
                    "tool_call_id": tool_call_id
                })
            # 重新把消息发送给大模型，让大模型生成最终回应
            response_final = self.deepseek.chat.completions.create(
                model="deepseek-chat",
                messages=messages
            )
            print(response_final.choices[0].message.content)
        else:
            print("没有调用自定义工具给大模型")
            print(deepseek_response.choices[0].message.content)

    async def aclose(self):
        await self.exit_stack.aclose()

async def main():
    client = MCPClient(server_path="./server.py")
    try:
        await client.run("计算9+9")
    finally:
        await client.aclose()  # 对上下文操作统一进行清理工作,不管程序运行正常与否都要进行清理


if __name__ == '__main__':
    asyncio.run(main())

