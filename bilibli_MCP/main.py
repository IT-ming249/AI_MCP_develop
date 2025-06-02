import asyncio
import json

import PIL.features
from mcp.server import FastMCP
from bilibili_api import search
from bilibili_api.search import SearchObjectType
from playwright.async_api import async_playwright, expect

#B站API文档 https://nemo2011.github.io/bilibili-api/#/README

app = FastMCP("bilibili-mcp")

#获取视频信息
@app.tool()
async def search_video(keyword:str, page:int=1):
    """
    在B站上搜索指定关键词的视频
    :param keyword: 用户输入的关键字
    :param page: 页码
    :return: 在B站上搜索后的结果
    """
    result = await search.search_by_type(keyword=keyword, page=page, search_type=SearchObjectType.VIDEO)
    return_result = {
        "page": page,
        "page_size": result["pagesize"],
        "num_pages": result["numPages"],
        "videos": [{
            "id":video["id"],
            "author":video["author"],
            "bvid":video["bvid"],
            "title":video["title"],
            "description":video["description"],
            "tag":video["tag"],
            "pubdate":video["pubdate"],
            "duration":video["duration"],
            "like":video["like"],
            "favorites":video["favorites"],
            "play":video["play"]
        }for video in result["result"]]
    }
    return return_result

@app.tool()
async def bilibili_login(phone:str, password:str):
    """
    输入手机号和密码来登录bilibili,登录过程中可能需要用户自己处理图形/短信验证吗，登录成果则返回cookie信息，失败则返回False
    :param phone: 登录手机号
    :param password: 登录密码
    :return: 如果登录成果则返回登录成功后的cookie,失败则返回false
    """
    async with async_playwright() as p:
        # 打开浏览器 并让浏览器显示出来
        browser = await p.chromium.launch(headless=False)
        # 创建上下文
        context = await browser.new_context()
        # 创建页面
        page = await context.new_page()
        await page.goto("https://www.bilibili.com")

        # 1. 先确保网页加载完成
        await page.wait_for_load_state(state="domcontentloaded")
        # 2. 寻找登录icon(登录按钮 F12找div class)，并点击
        await page.locator(".header-login-entry").click()
        # 3. 寻找账号/密码的输入框，并输入
        await page.get_by_placeholder(text="请输入账号").fill(phone)
        await page.get_by_placeholder(text="请输入密码").fill(password)
        # 4. 寻找登录按钮并执行点击操作
        await page.locator(".btn_primary").click()

        # 先等待验证码界面出现
        await page.wait_for_selector(".geetest_widget", state="visible")
        # 等待用户操作验证码(即验证码界面消失)
        await page.wait_for_selector(".geetest_widget", state="hidden")
        # 等待页面跳转
        await page.wait_for_timeout(3000)

        # 图形验证码操作完成用户，可能还需要验证短信验证码
        # 若登录成功，首页标题如下，这里做个期望
        await expect(page).to_have_title("哔哩哔哩 (゜-゜)つロ 干杯~-bilibili",timeout=120000)

        cookies = await context.cookies()
        return_cookies = dict()
        for cookie in cookies:
            if cookie["name"] == "SESSDATA":
                return_cookies["SESSDATA"] = cookie["value"]
            elif cookie["name"] == "bili_jct":
                return_cookies["bili_jct"] = cookie["value"]
        if return_cookies:
            return return_cookies
        else:
            return False

        #await page.wait_for_timeout(1000000)



# async def main():
#     #result = await search_video("搞笑")
#     result = await bilibili_login("", "")
#     print(result)


if __name__ == "__main__":
    app.run(transport="sse")
    #asyncio.run(main())