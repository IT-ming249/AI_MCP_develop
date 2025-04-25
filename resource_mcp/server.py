from mcp.server.fastmcp import FastMCP
import aiofiles

app = FastMCP("demo resource")

#资源，提供文本/图片/网页 或其它数据给大模型
@app.resource(
    uri="file://10560_152209015_ZY.txt",  #uri 可自定义，能唯一匹配上就行
    name="file_resourse",
    description="作者何浩明的毕业论文中英文摘要",  #区别于tools,资源的描述在这写
    mime_type="text/plain",
)
async def file_resourse_to_model():
    #打开文件获取数据
    async with aiofiles.open("./data/10560_152209015_ZY.txt", mode="r",encoding='utf-8') as fp:
        content = await fp.read()
    return content



if __name__ == "__main__":
    app.run(transport="sse")