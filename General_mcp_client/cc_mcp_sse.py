from fastmcp import FastMCP, Context
from functools import wraps
import inspect

#用来测试本地MCPserver的使用
app = FastMCP("plus mcp")

def get_header():
    def wrapper(func):
        @wraps(func)
        async def wrapped(*args, **kwargs):
            ctx = app.get_context() #获取上下文
            request = ctx.get_http_request()
            print(request.headers)
            if inspect.iscoroutinefunction(func): #判断是否为协程
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        return wrapped
    return wrapper

#工具的描述一定要写，否则大模型无法理解这个工具的功能
@app.tool()
@get_header()
def plus_tool(a:float, b:float, ctx: Context) -> float:
    """
    计算两数之和的工具
    :param a: 第一个相加的数
    :param b: 第二个相加的数
    :return: 返回两数相加后的结果
    """
    return a + b

if __name__ == "__main__":
    app.run(transport="sse")