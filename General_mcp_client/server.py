# 存放一些和服务器交互的类
import asyncio
from enum import Enum
from typing import Any
from pydantic import AnyUrl
from mcp.client.session import ClientSession
from contextlib import AsyncExitStack
from mcp.client.stdio import StdioServerParameters,stdio_client
from mcp.client.sse import sse_client
from mcp.shared.exceptions import McpError
from models import MCPFunction, MCPFunctionType

class MCPTransport(Enum):
    # 枚举类型 指定通信方式
    STDIO = "stdio"
    SSE = "sse"

class MCPServer:
    """
    代表一个MCP Server，封装MCP Server 的连接 通信
    """
    def __init__(self,
                 name: str,
                 transport: MCPTransport=MCPTransport.STDIO,
                 cmd: str | None = None,
                 args: list[str] | None = None,
                 env: dict[str, str] | None = None,
                 url: str | None = None,):
        self.name = name
        self.transport = transport
        if self.transport == MCPTransport.STDIO:
            #断言指定不能为空
            assert cmd is not None
            assert args is not None
            self.cmd = cmd
            self.args = args
            self.env = env
        else:
            assert url is not None
            self.url = url
        #异步上下文堆栈
        self._exit_stack = AsyncExitStack()
        #与服务器通信的session对象
        self.session: ClientSession | None = None
        # 保存当前MCP Server的所有function (T\T\R\R)'
        self.functions: dict[str, MCPFunction] = {}
    async def initialize(self):
        # 初始化操作，连接好MCP server，以及获取Session对象,Tools,promote,Resource
        if self.transport == MCPTransport.STDIO:
            params = StdioServerParameters(
                command=self.cmd,
                args=self.args,
                env=self.env)
            read_stream, write_stream = await self._exit_stack.enter_async_context(stdio_client(params))
            self.session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream))
        else:
            read_stream, write_stream = await self._exit_stack.enter_async_context(
                # headers 传递请求头信息
                sse_client(self.url, headers={"Authorization": "Bearer tokenSample"}))
            self.session = await self._exit_stack.enter_async_context(ClientSession(read_stream, write_stream))
        await self.session.initialize()
        # 获取所有的Tool Resource Promote
        await self.fetch_function()


    async def fetch_function(self):
        assert self.session is not None
        # 获取tool
        try:
            tools = (await self.session.list_tools()).tools
        except McpError:
            tools =[]
        for tool in tools:
            tool_name = tool.name.replace(" ","_")
            self.functions[tool_name] = MCPFunction(
            name = tool_name,
            origin_name = tool.name,
            server_name = self.name,
            description = tool.description,
            type_ = MCPFunctionType.TOOL,
            input_schema = tool.inputSchema,
            )
        # 获取resource/resource_template
        try:
            resources = (await self.session.list_resources()).resources
        except McpError:
            resources = []
        for resource in resources:
            resource_name = resource.name.replace(" ","_")
            self.functions[resource_name] = MCPFunction(
                name = resource_name,
                origin_name = resource.name,
                server_name = self.name,
                description = resource.description,
                type_ = MCPFunctionType.RESOURCE,
                # uri是AnyUrl类型
                uri = resource.uri,
            )
        try:
            resource_templates = (await self.session.list_resource_templates()).resourceTemplates
        except McpError:
            resource_templates = []
        for resource_template in resource_templates:
            resource_template_name=resource_template.name.replace(" ","_")
            self.functions[resource_template_name] = MCPFunction(
                name = resource_template_name,
                origin_name = resource_template.name,
                server_name = self.name,
                description = resource_template.description,
                type_ = MCPFunctionType.RESOURCE_TEMPLATE,
                # uriTemplate 是字符串类型
                uri = resource_template.uriTemplate,
            )
        # 获取prompt
        try:
            prompts = (await self.session.list_prompts()).prompts
        except McpError:
            prompts=[]
        for prompt in prompts:
            prompt_name=prompt.name.replace(" ","_")
            self.functions[prompt_name] = MCPFunction(
                name = prompt_name,
                origin_name = prompt.name,
                server_name = self.name,
                description = prompt.description,
                type_ = MCPFunctionType.PROMPT,
                arguments = prompt.arguments,
            )
    async def call_functions(self,name , arguments: dict[str, Any]):
        function = self.functions[name]
        if function.type_ == MCPFunctionType.TOOL:
            response = await self.session.call_tool(name=function.origin_name, arguments=arguments)
            return response.content[0].text
        elif function.type_ == MCPFunctionType.RESOURCE:
            response = await self.session.read_resource(uri=function.uri)
            return response.contents[0].text
        elif function.type_ == MCPFunctionType.RESOURCE_TEMPLATE:
            uri = AnyUrl(function.uri.format(**arguments))
            response = await self.session.read_resource(uri=uri)
            return response.contents[0].text
        else:
            response = await self.session.get_prompt(name=function.origin_name,arguments=arguments)
            return response.content.text

    #释放异步堆栈资源
    async def aclose(self):
        await self._exit_stack.aclose()

    #定义一进入类的行为
    async def __aenter__(self):
        await self.initialize()
        return self
    #定义推出类的行为
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()

class MCPServerManager:
    def __init__(self, mcp_dicts: dict):
        self.mcp_dict = mcp_dicts
        self.servers: dict[str, MCPServer] = {}
        self._exit_stack = AsyncExitStack()
        self.all_functions: dict[str, MCPFunction] = {}
    async def initialize(self):
        for name,mcp_dict in self.mcp_dict.items():
            # 1. 连接创建所有MCP Server对象
            if mcp_dict.get("command"):
                transport = MCPTransport.STDIO
            else:
                transport = MCPTransport.SSE
            server = await self._exit_stack.enter_async_context(
                MCPServer(
                    name=name,
                    transport=transport,
                    cmd=mcp_dict.get("command"),
                    args=mcp_dict.get("args"),
                    env=mcp_dict.get("env"),
                    url=mcp_dict.get("url")
                )
            )
            self.servers[name] = server
            #2. 获取所有MCP Server的函数并保存
            self.all_functions.update(server.functions)

    async def call_functions(self,name , arguments: dict[str, Any]|None=None):
        function = self.all_functions[name]
        server = self.servers[function.server_name]
        return await server.call_functions(name, arguments)

    async def aclose(self):
        await self._exit_stack.aclose()

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()



#简单测试一下
async def main():
    async with MCPServer(
        name = "filesystem",
        cmd = 'npx',
        args=['-y', "@modelcontextprotocol/server-filesystem",
              "C:/Users/10451/Desktop"]
    ) as server:
        print(server.functions)
        # result =await server.call_functions("read_file",{"path":"C:/Users/10451/Desktop/abx.txt"})
        # print(result)

if __name__ == '__main__':
    asyncio.run(main())

