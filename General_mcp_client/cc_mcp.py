#from mcp.server.fastmcp import FastMCP

#sse服务端导入fastMCP通过如下方式：
from fastmcp import FastMCP,Context
""" 使用stdio时在mcp.json加入
"ccmcp": {
      "command": "python",
      "args": [
        "cc_mcp.py"
      ],
      "env": {
        "Authorization": "Bearer tokenSample"
      }
    },
"""
#用来测试本地MCPserver的使用
app = FastMCP("start mcp")

#工具的描述一定要写，否则大模型无法理解这个工具的功能
@app.tool()
def plus_tool(a:float, b:float) -> float:
    """
    计算两数之和的工具
    :param a: 第一个相加的数
    :param b: 第二个相加的数
    :return: 返回两数相加后的结果
    """

    #获取请求头信息
    return a + b

if __name__ == "__main__":
    app.run(transport="stdio")