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
api_key = os.getenv('AZURE_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GOOGLE_ENGIN_ID = os.getenv('GOOGLE_ENGIN_ID')

LINE_API = LineBotApi(os.getenv('LINE_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_SECRET'))

histories = [{"role":"system", "content": ""}]
system_prompt = "請根據內容適當使用可愛的顏文字回覆，使用繁體中文，當你不確定使用者的問題時，請回答「不知道」"

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
    api_key=api_key,
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
    
    reply = chat_prompt(text, system_prompt, 0.1)

    print('===== reply =====')
    print(reply)

    LINE_API.reply_message(event.reply_token, TextSendMessage(text=reply))



def chat_prompt(pmt, sys_pmt , temperature = 0.0):
    print('===== Call chat_prmopt function =====')
    histories[0] = {"role":"system", "content": sys_pmt}

    def make_tool_back_msg(tool_msg):
        msg_json = tool_msg.model_dump()
        if msg_json['tool_calls']:
            tool_back_msg = {
                'content': msg_json['content'],
                'role': msg_json['role'],
                'tool_calls': msg_json['tool_calls'] if msg_json['tool_calls'] else "None",
                'tool_call_id': msg_json['tool_calls'][0]['id'] if msg_json['tool_calls'] else "None",
                'name': msg_json['tool_calls'][0]['function']['name'] if msg_json['tool_calls'] else "None",
            }
        else:
            tool_back_msg = {
                'content': msg_json['content'],
                'role': msg_json['role'],
            }
        return tool_back_msg


    # Step01: 準備 Function to be called
    def google_res(user_msg, num_results=5, google_res=False, verbose=False):
        print('===== 啟動 google.search =====')
        content = "以下為已發生的事實：\n"
        for res in google.search(user_msg):
            content += f"標題：{res.title}\n摘要：{res.snippet}\n\n"
        content += "請依照上述事實回答以下問題。\n"
        print(content)
        return content



    def get_osu_rankings_data(mode='osu', length=50):
        print("=========== Start get_osu_rankings_data ===========")
        url = f"https://osu-rankings-crawler.onrender.com/api/country_rankings?mode={mode}&length={length}"
        response = requests.get(url=url)
        response.raise_for_status()
        json_data = str(response.json())
        print(json_data, end='\n\n')

        return json_data


    # Step02: 定義 Function info to be mapped

    get_osu_rankings_data_tool = {
        "type": "function",
        "function": {
            "name": "get_osu_rankings_data",
            "description": (
                "Retrieve ranking data for osu! (a rhythm game) by specifying the game mode and the number of rankings. "
                "The response will be a JSON object with the following structure: "
                "{'active_users': [63149, 119636], 'avg_performance': [665, 211], 'avg_score': [35143981, 12080189], "
                "'country_name': ['Japan', 'United States'], 'performance': [41990612, 25257620], "
                "'play_count': [33432194, 25999158], 'ranking': [1, 2]}."),
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "description": (
                            "The game mode for which to retrieve rankings ('osu', 'taiko', 'fruits', 'mania'). "
                            "Default is 'osu'."
                        ),
                    },
                    "length": {
                        "type": "number",
                        "description": (
                            "The number of rankings to retrieve. Default is 50."
                        ),
                    }
                },
                "required": ["mode", "length"],
            },
        }
    }

    google_search_tool = {
            "type":"function",
            "function": {
                "name": "google_res",
                "description": "當遇到超過時間範圍的資料，利用 Google 取得搜尋結果",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_msg": {
                            "type": "string",
                            "description": "要搜尋的關鍵字",
                        }
                    },
                    "required": ["user_msg"],
                },
            }
        }

    histories.append({"role":"user", "content": pmt})

    # Step03: 第一次執行取回需要執行的 Function
    response = client.chat.completions.create(
        model = "gpt-4-0409-60k",
        messages = histories,
        tools = [google_search_tool, get_osu_rankings_data_tool],
        tool_choice = "auto",
        temperature = temperature,
    )

    histories.append(make_tool_back_msg(response.choices[0].message))

    if(response.choices[0].message.tool_calls):
        tool_call = response.choices[0].message.tool_calls[0]
        func_name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        print(f'args: {args}')

        args_list = [value for key, value in args.items()]
        print(f"args_list: {args_list}")

        args_str = ""
        for arg in args_list:
            args_str += f"'{arg}', " if type(arg) == str else f"{arg}, "

        print(f"args_str: {args_str}")

        print('func_name: ', func_name)
        print(f'function call: {func_name}({args_str})')

        # Step05: 第二次執行會先執行 Function 後再將結果傳給 Model
        histories.append(
            {
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": func_name,
                "content": eval(f'{func_name}({args_str})')
            })

        response = client.chat.completions.create( model='gpt-4-0409-60k', messages=histories, temperature = temperature)
        histories.append(make_tool_back_msg(response.choices[0].message))

    print('===== histories =====')
    print(histories)
    print('===== response =====')
    print(response.choices[0].message.content)

    return response.choices[0].message.content

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

