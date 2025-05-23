#我们可以在服务端提前定义好一套完整的提示词，当客户端需要完成某个任务时，
#直接从服务器上获取提示词， 再把提示词交给大模型，可以使得我们的任务更加流畅的完成。
#就是针对某一个问题，给一套提示词模板

from mcp.server import FastMCP

app = FastMCP("prompt demo")

@app.prompt()
def policy_prompt(policy: str):
    """
    能够对用户提供的政策内容，对其进行总结、提取关键信息的提示词模板
    : param policy: 需要总结的政策内容
    : return: 总结政策的提示词模板
    """

    # 如果直接返回一个字符串，在客户端接收到的是一个PromptMessage对象
    # 这个对象默认的role为user
    # 想要返回其它role 就必须第一为字典的形式
    return [{
        "role": "user",
        "content": f"""
            这个是政策内容：“{policy}”，请对该政策内容进行总结，总结的规则为：
            1. 提取政策要点。
            2. 针对每个政策要点按照以下格式进行总结：
                * 要点标题：政策的标题，要包含具体的政策信息
                * 针对人群：政策针对的人群
                * 有效时间：政策执行的开始时间和结束时间
                * 相关部门：政策是由哪些部门执行
            总结的内容不要太官方，用通俗易懂的语言。
            """
    }]

if __name__ == '__main__':
    app.run(transport="sse")

