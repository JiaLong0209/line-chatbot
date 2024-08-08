# 將 LineBot 串接 ChatGPT API

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    TextMessage,
    TextSendMessage,
)
import os

# import googlesearch

api = LineBotApi(os.getenv('LINE_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_SECRET'))
messages = [{
    "role":
    "system",
    "content":
    "Please use Chinese Traditional, and remember what I said. 回答請根據內容使用可愛的顏文字"
}, {
    "role": "system",
    "content": "當你不確定使用者的問題時，請回答「不知道」"
}]

app = Flask(__name__)


@app.get("/")
def hello():
    return 'Hello World!'


@app.post("/")
def callback():
    # 取得 X-Line-Signature 表頭電子簽章內容
    signature = request.headers['X-Line-Signature']

    # 以文字形式取得請求內容
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # 比對電子簽章並處理請求內容
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("電子簽章錯誤, 請檢查密鑰是否正確？")
        abort(400)

    return 'OK'


import openai

client = openai.AzureOpenAI(
    api_key=os.getenv('AZURE_API_KEY'),
    api_version="2023-12-01-preview",
    azure_endpoint="https://bllm02apikey01.openai.azure.com/")


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    print('===== handle_message(event) =====')
    print(event)

    print('===== user_id =====')
    user_id = event.source.user_id
    print(user_id)

    print('===== text =====')
    text = event.message.text.strip()
    print(text)
    messages.append({"role": "user", "content": text})

    response = client.chat.completions.create(model="gpt-35-turbo-120",
                                              messages=messages)
    reply = response.choices[0].message.content

    print('===== reply =====')
    print(reply)
    messages.append({"role": "assistant", "content": reply})

    api.reply_message(event.reply_token, TextSendMessage(text=reply))

    print('===== history =====')
    print(messages)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

