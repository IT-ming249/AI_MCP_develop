from mcp.server.fastmcp import FastMCP, Context
from mcp.types import RequestParams, SamplingMessage, TextContent
import asyncio

app = FastMCP("context mcp")

#context上下文只能在tools中实现，并需要在工具函数中指定Context类型的参数

#contex服务端记录日志
#@app.tool()  #将该装饰器注释掉，可以将工具函数变成普通函数
async def log_tool(files: list[str], ctx: Context):
    for i in range(len(files)):
        #下面模拟一个文件处理的过程
        await asyncio.sleep(1)
        await ctx.info(message=f"文件{i}处理完成")
    return "所有文件都处理完成"

#context进度反馈
#@app.tool()
async def progress_tool(files: list[str], ctx: Context):
    for i in range(len(files)):
        #下面模拟一个文件处理的过程↓
        await asyncio.sleep(1)
        #发送进度反馈报告  Token是字符串或整形 可以设置成一个唯一的uuid，以便知道是哪个任务在执行
        ctx.request_context.meta = RequestParams.Meta(progressToken=1)
        #progress 表示当前进度 total表示任务总长度
        await ctx.report_progress(progress=(i+1)/len(files), total=len(files))

#服务端调用大模型
@app.tool()
async def sampling_tool(ctx: Context):
    response = await ctx.session.create_message(
        messages=[SamplingMessage(
        role="user",
        content=TextContent(
        type="text",
        text="介绍一下你自己",
        ))],
    max_tokens=2048)
    print(response)
    return "采样成功"



if __name__ == "__main__":
    app.run(transport="sse")