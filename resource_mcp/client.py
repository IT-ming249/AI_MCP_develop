from openai import OpenAI
from mcp.client.sse import sse_client
from mcp import ClientSession
import asyncio
from contextlib import AsyncExitStack

import const

class MCPClient:
    def __init__(self,):
        self.deepseek = OpenAI(
            api_key=const.API_KEY,
            base_url=const.BASE_URL
        )
        self.exit_stack = AsyncExitStack()
        self.resources = {}

    async def run(self,query: str):
        # 1. 创建读写流通道 sse_client接收服务端url/sse
        read_stream, write_stream = await self.exit_stack.enter_async_context(sse_client(url="http://127.0.0.1:8000/sse"))

        # 2. 创建客户端与服务端进行通信的session对象  : 指定类型方便后续提示
        session: ClientSession = await self.exit_stack.enter_async_context(ClientSession(read_stream,write_stream))

        # 3. 初始化通信
        await session.initialize()

        #获取服务端提供的所有资源
        resources = (await session.list_resources()).resources
        #print(resources)
        resources_func = []
        for resource in resources:
            uri = resource.uri
            name = resource.name
            description = resource.description
            mimeType = resource.mimeType
            #保存资源↓
            self.resources[name] = {
                "uri": uri,
                "name": name,
                "description": description,
                "mime_type": mimeType
            }

            #资源转为function calling格式↓
            resources_func.append({
                "type": "function",
                "function":{
                    "name":name,
                    "description":description,
                    #资源没有输入参数inputSchema为空
                    "inputSchema":None
                }
            })

            #创建消息发送给大模型
            messages = [{
                "role":"user",
                "content":query
            }]
            deepseek_response = self.deepseek.chat.completions.create(
                messages = messages,
                model = "deepseek-chat",
                tools = resources_func,
            )
            #print(deepseek_response)
            choice = deepseek_response.choices[0]
            if choice.finish_reason == "tool_calls":
                # 为了后期，大模型能更加精准的恢复，把大模型选择的工具的message，添加到messages中
                messages.append(choice.message.model_dump())
                tool_calls = choice.message.tool_calls
                for tool_call in tool_calls:
                    tool_call_id = tool_call.id
                    # 下面几个参数是工具调用用到的
                    # function = tool_call.function
                    # function_arguments = json.loads(function.arguments)
                    # function_name = function.name
                    uri = self.resources[name]["uri"]

                    #执行资源调用(这是MCP server返回的响应，不是大模型的)
                    resources_response = await session.read_resource(uri=uri)
                    #print(resources_response)
                    result = resources_response.contents[0].text

                    #把资源响应结果放入大模型的信息中
                    messages.append({
                        "role":"tool",
                        "content":result,
                        "tool_call_id":tool_call_id,
                    })
                response_finally = self.deepseek.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages
                )
                print(response_finally.choices[0].message.content)

            else:
                print("大模型没有调用自定义工具或资源")
                print(deepseek_response.choices[0].message.content)

    async def aclose(self):
        await self.exit_stack.aclose()

async def main():
    client = MCPClient()
    try:
        await client.run("简述一下何浩明的毕业论文工作")
    finally:
        await client.aclose()

if __name__ == '__main__':
    asyncio.run(main())
