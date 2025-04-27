from openai import OpenAI
from mcp.client.sse import sse_client
from mcp import ClientSession
import asyncio
import json
from contextlib import AsyncExitStack



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
        session: ClientSession = await self.exit_stack.enter_async_context(ClientSession(read_stream,write_stream))

        # 3. 初始化通信 (三步固定流程)
        await session.initialize()

        # 获取MCP server的所有提示词
        response_mcp = await session.list_prompts()
        prompts = response_mcp.prompts
        #print(prompts)

        #所有提示词转成function calling格式
        prompts_func = []
        for prompt in prompts:
            name = prompt.name
            description = prompt.description
            prompts_func.append({
                "type":"function",
                "function": {
                    "name":name,
                    "description": description,
                    "inputSchema": None
                }
            })
            #保存提示词信息
            self.prompts[name] = {
                "name": name,
                "description": description,
                "argumemts": [argument.model_dump() for argument in prompt.arguments],
            }

        messages = [{
            "role":"user",
            "content":query
        }]

        first_response = self.deepseek.chat.completions.create(
            messages=messages,
            model="deepseek-chat",
            tools=prompts_func
        )
        choice = first_response.choices[0]

        if choice.finish_reason == "tool_calls":
            messages.append(choice.message.model_dump())
            tool_calls = choice.message.tool_calls
            for tool_call in tool_calls:
                tool_call_id = tool_call.id
                function = tool_call.function
                function_name = function.name
                function_arguments = json.loads(function.arguments)
                # 获取提示词，从mcp服务器
                prompts_response = await session.get_prompt(name=function_name,arguments=function_arguments)
                # 解决openai.BadRequestError bug 需要先添加tool的message
                messages.append({
                    "role":"tool",
                    "content":prompts_response.messages[0].content.text,
                    "tool_call_id":tool_call_id,
                })
            final_response = self.deepseek.chat.completions.create(
                messages=messages,
                model="deepseek-chat",
            )
            print(final_response.choices[0].message.content)
        else:
            print("大模型没有调用自定义工具或资源")
            print(first_response.choices[0].message.content)



    async def aclose(self):
        await self.exit_stack.aclose()

async def main():
    client = MCPClient()
    try:
        with open("./data/plt.txt",mode="r",encoding="utf-8") as f:
            policy = f.read()
        await client.run(f"总结一下这个政策{policy}")
    finally:
        await client.aclose()  # 对上下文操作统一进行清理工作,不管程序运行正常与否都要进行清理

if __name__ == '__main__':
    asyncio.run(main())
