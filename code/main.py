import os,base64,requests
import google.cloud.dialogflow_v2 as dialogflow
from flask import Flask, request
from flask_ngrok import run_with_ngrok

# 載入 json 標準函式庫，處理回傳的資料格式
import requests, json, time, statistics

# 載入 LINE Message API 相關函式庫
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage


os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = 'code\key.json' # 金鑰 json
project_id = 'newagent-kxxt'                                   # dialogflow project id
language = 'en'                                                # 語系
session_id = 'ruichen'                                         # 自訂 session id


# LINE 回傳圖片函式
def reply_image(msg, rk, token):
    headers = {'Authorization':f'Bearer {token}','Content-Type':'application/json'}    
    body = {
    'replyToken':rk,
    'messages':[{
          'type': 'image',
          'originalContentUrl': msg,
          'previewImageUrl': msg
        }]
    }
    req = requests.request('POST', 'https://api.line.me/v2/bot/message/reply', headers=headers,data=json.dumps(body).encode('utf-8'))
    print(req.text)

# 地震資訊函式
def earth_quake():
    msg = ['找不到地震資訊','https://example.com/demo.jpg']                     # 預設回傳的訊息
    try:
        code = 'CWA-53CDB49E-D455-4018-BE72-36E6B6700123'
        url = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/E-A0016-001?Authorization={code}'
        e_data = requests.get(url)                                             # 爬取地震資訊網址
        e_data_json = e_data.json()                                            # json 格式化訊息內容
        eq = e_data_json['records']['Earthquake']                              # 取出地震資訊
        for i in eq:
            loc = i['EarthquakeInfo']['Epicenter']['Location']                 # 地震地點
            val = i['EarthquakeInfo']['EarthquakeMagnitude']['MagnitudeValue'] # 地震規模
            dep = i['EarthquakeInfo']['FocalDepth']                            # 地震深度
            eq_time = i['EarthquakeInfo']['OriginTime']                        # 地震時間
            img = i['ReportImageURI']                                          # 地震圖
            msg = [f'{loc}，芮氏規模 {val} 級，深度 {dep} 公里，發生時間 {eq_time}。', img]
            break     # 取出第一筆資料後就 break
        return msg    # 回傳 msg
    except:
        return msg    # 如果取資料有發生錯誤，直接回傳 msg

# LINE push 訊息函式
def push_message(msg, uid, token):
    headers = {'Authorization':f'Bearer {token}','Content-Type':'application/json'}   
    body = {
    'to':uid,
    'messages':[{
            "type": "text",
            "text": msg
        }]
    }
    req = requests.request('POST', 'https://api.line.me/v2/bot/message/push', headers=headers,data=json.dumps(body).encode('utf-8'))
    print(req.text)

# LINE 回傳訊息函式
def reply_message(msg, rk, token):
    headers = {'Authorization':f'Bearer {token}','Content-Type':'application/json'}
    body = {
    'replyToken':rk,
    'messages':[{
            "type": "text",
            "text": msg
        }]
    }
    req = requests.request('POST', 'https://api.line.me/v2/bot/message/reply', headers=headers,data=json.dumps(body).encode('utf-8'))
    print(req.text)

# LINE 回傳圖片函式
def reply_image(msg, rk, token):
    headers = {'Authorization':f'Bearer {token}','Content-Type':'application/json'}
    body = {
    'replyToken':rk,
    'messages':[{
          'type': 'image',
          'originalContentUrl': msg,
          'previewImageUrl': msg
        }]
    }
    req = requests.request('POST', 'https://api.line.me/v2/bot/message/reply', headers=headers,data=json.dumps(body).encode('utf-8'))
    print(req.text)

# 目前天氣函式
def current_weather(address):
    city_list, area_list, area_list2 = {}, {}, {} # 定義好待會要用的變數
    msg = '找不到氣象資訊。'                         # 預設回傳訊息

    # 定義取得資料的函式
    def get_data(url):
        w_data = requests.get(url)   # 爬取目前天氣網址的資料
        w_data_json = w_data.json()  # json 格式化訊息內容
        location = w_data_json['cwaopendata']['dataset']['Station']  # 取出對應地點的內容
        for i in location:
            name = i['StationName']                       # 測站地點
            city = i['GeoInfo']['CountyName']     # 縣市名稱
            area = i['GeoInfo']['TownName']     # 鄉鎮行政區
            dailyhigh = check_data(i['WeatherElement']['DailyExtreme']['DailyHigh']['TemperatureInfo']['AirTemperature'])
            dailylow = check_data(i['WeatherElement']['DailyExtreme']['DailyLow']['TemperatureInfo']['AirTemperature'])
            temp = check_data(i['WeatherElement']['AirTemperature'])                         # 氣溫
            humd = check_data(round(float(i['WeatherElement']['RelativeHumidity'] )*1,1)) # 相對濕度
            r24 = check_data(i['WeatherElement']['Now']['Precipitation'])                    # 累積雨量
            if area not in area_list:
                area_list[area] = {'temp':temp, 'humd':humd, 'r24':r24, 'dailyhigh':dailyhigh, 'dailylow':dailylow}  # 以鄉鎮區域為 key，儲存需要的資訊
            if city not in city_list:
                city_list[city] = {'temp':[], 'humd':[], 'r24':[], 'dailyhigh':[], 'dailylow':[]}       # 以主要縣市名稱為 key，準備紀錄裡面所有鄉鎮的數值
            city_list[city]['temp'].append(temp)               # 記錄主要縣市裡鄉鎮區域的溫度 ( 串列格式 )
            city_list[city]['humd'].append(humd)               # 記錄主要縣市裡鄉鎮區域的濕度 ( 串列格式 )
            city_list[city]['r24'].append(r24)                 # 記錄主要縣市裡鄉鎮區域的雨量 ( 串列格式 )
            city_list[city]['dailyhigh'].append(dailyhigh)     # 記錄主要縣市裡鄉鎮區域最高溫 ( 串列格式 )
            city_list[city]['dailylow'].append(dailylow)       # 記錄主要縣市裡鄉鎮區域最低溫 ( 串列格式 )

    # 定義如果數值小於 0，回傳 False 的函式
    def check_data(e):
        return False if float(e)<0 else float(e)

    # 定義產生回傳訊息的函式
    def msg_content(loc, msg):
        a = msg
        for i in loc:
            if i in address: # 如果地址裡存在 key 的名稱
                temp = f"氣溫 {loc[i]['temp']} 度" if loc[i]['temp'] != False else ''
                dailyhigh = f"\n最高溫 {loc[i]['dailyhigh']}度" if loc[i]['dailyhigh'] != False else ''
                dailylow = f"\n最低溫 {loc[i]['dailylow']}度" if loc[i]['dailylow'] != False else ''
                humd = f"\n相對濕度 {loc[i]['humd']}%" if loc[i]['humd'] != False else ''
                r24 = f"\n累積雨量 {loc[i]['r24']}mm" if loc[i]['r24'] != False else ''
                description = f'{temp}{dailyhigh}{dailylow}{humd}{r24}'
                a = f'{description}' # 取出 key 的內容作為回傳訊息使用
                break
        return a

    try:
        # 因為目前天氣有兩組網址，兩組都爬取
        code = 'CWA-53CDB49E-D455-4018-BE72-36E6B6700123'
        get_data(f'https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/O-A0001-001?Authorization={code}&downloadType=WEB&format=JSON')
        get_data(f'https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/O-A0003-001?Authorization={code}&downloadType=WEB&format=JSON')

        for i in city_list:
            if i not in area_list2: # 將主要縣市裡的數值平均後，以主要縣市名稱為 key，再度儲存一次，如果找不到鄉鎮區域，就使用平均數值
                area_list2[i] = {'temp':round(statistics.mean(city_list[i]['temp']),1),
                                'humd':round(statistics.mean(city_list[i]['humd']),1),
                                'r24':round(statistics.mean(city_list[i]['r24']),1),
                                'dailyhigh':round(statistics.mean(city_list[i]['dailyhigh']),1),
                                'dailylow':round(statistics.mean(city_list[i]['dailylow']),1)
                                }
        msg = msg_content(area_list2, msg)  # 將訊息改為「大縣市」
        msg = msg_content(area_list, msg)   # 將訊息改為「鄉鎮區域」
        return msg    # 回傳 msg
    except:
        print(Exception)
        return msg    # 如果取資料有發生錯誤，直接回傳 msg

# 氣象預報函式
def forecast(address):
    area_list = {}
    # 將主要縣市個別的 JSON 代碼列出
    json_api = {"宜蘭縣":"F-D0047-001","桃園市":"F-D0047-005","新竹縣":"F-D0047-009","苗栗縣":"F-D0047-013",
            "彰化縣":"F-D0047-017","南投縣":"F-D0047-021","雲林縣":"F-D0047-025","嘉義縣":"F-D0047-029",
            "屏東縣":"F-D0047-033","臺東縣":"F-D0047-037","花蓮縣":"F-D0047-041","澎湖縣":"F-D0047-045",
            "基隆市":"F-D0047-049","新竹市":"F-D0047-053","嘉義市":"F-D0047-057","臺北市":"F-D0047-061",
            "高雄市":"F-D0047-065","新北市":"F-D0047-069","臺中市":"F-D0047-073","臺南市":"F-D0047-077",
            "連江縣":"F-D0047-081","金門縣":"F-D0047-085"}
    msg = '找不到天氣預報資訊。'    # 預設回傳訊息
    try:
        code = 'CWA-53CDB49E-D455-4018-BE72-36E6B6700123'
        url = f'https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/F-C0032-001?Authorization={code}&downloadType=WEB&format=JSON'
        f_data = requests.get(url)   # 取得主要縣市預報資料
        f_data_json = f_data.json()  # json 格式化訊息內容
        location = f_data_json['cwaopendata']['dataset']['location']  # 取得縣市的預報內容
        for i in location:
            city = i['locationName']    # 縣市名稱
            wx8 = i['weatherElement'][0]['time'][0]['parameter']['parameterName']    # 天氣現象
            mint8 = i['weatherElement'][2]['time'][0]['parameter']['parameterName']  # 最低溫
            maxt8 = i['weatherElement'][1]['time'][0]['parameter']['parameterName']  # 最高溫
            ci8 = i['weatherElement'][3]['time'][0]['parameter']['parameterName']    # 舒適度
            pop8 = i['weatherElement'][4]['time'][0]['parameter']['parameterName']   # 降雨機率
            area_list[city] = f'未來八小時{wx8}。最高溫 {maxt8} 度。最低溫 {mint8} 度。{ci8}。降雨機率 {pop8} %。'  # 組合成回傳的訊息，存在以縣市名稱為 key 的字典檔裡
        for i in area_list:
            if i in address:        # 如果使用者的地址包含縣市名稱
                msg = area_list[i]  # 將 msg 換成對應的預報資訊
                # 將進一步的預報網址換成對應的預報網址
                url = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/{json_api[i]}?Authorization={code}&elementName=WeatherDescription'
                f_data = requests.get(url)  # 取得主要縣市裡各個區域鄉鎮的氣象預報
                f_data_json = f_data.json() # json 格式化訊息內容
                location = f_data_json['records']['locations'][0]['location']    # 取得預報內容
                break
        for i in location:
            city = i['locationName']   # 取得縣市名稱
            wd = i['weatherElement'][0]['time'][1]['elementValue'][0]['value']  # 綜合描述
            if city in address:           # 如果使用者的地址包含鄉鎮區域名稱
                msg = f'未來八小時天氣{wd}' # 將 msg 換成對應的預報資訊
                break
        return msg  # 回傳 msg
    except:
        return msg  # 如果取資料有發生錯誤，直接回傳 msg
    
# 空氣品質函式
def aqi(address):
    city_list, site_list ={}, {}
    msg = '找不到空氣品質資訊。'
    try:
        # 2022/12 時氣象局有修改了 API 內容，將部份大小寫混合全改成小寫，因此程式碼也跟著修正
        url = 'https://data.epa.gov.tw/api/v2/aqx_p_432?api_key=e8dd42e6-9b8b-43f8-991e-b3dee723a52d&limit=1000&sort=ImportDate%20desc&format=JSON'
        a_data = requests.get(url)             # 使用 get 方法透過空氣品質指標 API 取得內容
        a_data_json = a_data.json()            # json 格式化訊息內容
        for i in a_data_json['records']:       # 依序取出 records 內容的每個項目
            city = i['county']                 # 取出縣市名稱
            if city not in city_list:
                city_list[city]=[]             # 以縣市名稱為 key，準備存入串列資料
            site = i['sitename']               # 取出鄉鎮區域名稱
            aqi = int(i['aqi'])                # 取得 AQI 數值
            status = i['status']               # 取得空氣品質狀態
            site_list[site] = {'aqi':aqi, 'status':status}  # 記錄鄉鎮區域空氣品質
            city_list[city].append(aqi)        # 將各個縣市裡的鄉鎮區域空氣 aqi 數值，以串列方式放入縣市名稱的變數裡
        for i in city_list:
            if i in address: # 如果地址裡包含縣市名稱的 key，就直接使用對應的內容
                # 參考 https://airtw.epa.gov.tw/cht/Information/Standard/AirQualityIndicator.aspx
                aqi_val = round(statistics.mean(city_list[i]),0)  # 計算平均數值，如果找不到鄉鎮區域，就使用縣市的平均值
                aqi_status = ''  # 手動判斷對應的空氣品質說明文字
                if aqi_val<=50: aqi_status = '良好'
                elif aqi_val>50 and aqi_val<=100: aqi_status = '普通'
                elif aqi_val>100 and aqi_val<=150: aqi_status = '對敏感族群不健康'
                elif aqi_val>150 and aqi_val<=200: aqi_status = '對所有族群不健康'
                elif aqi_val>200 and aqi_val<=300: aqi_status = '非常不健康'
                else: aqi_status = '危害'
                msg = f'空氣品質{aqi_status} ( AQI {aqi_val} )。' # 定義回傳的訊息
                break
        for i in site_list:
            if i in address:  # 如果地址裡包含鄉鎮區域名稱的 key，就直接使用對應的內容
                msg = f'空氣品質{site_list[i]["status"]} ( AQI {site_list[i]["aqi"]} )'
                break
        return msg    # 回傳 msg
    except:
        return msg    # 如果取資料有發生錯誤，直接回傳 msg

# dialogflow 處理自然語言
def dialogflowFn(text,reply_token,access_token,user_id):
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)
    text_input = dialogflow.types.TextInput(text=text, language_code=language)
    query_input = dialogflow.types.QueryInput(text=text_input)
    print(query_input)
    try:
        response = session_client.detect_intent(session=session, query_input=query_input)
        print("input:", response.query_result.query_text)
        print("intent:", response.query_result.intent.display_name)
        intent = response.query_result.intent.display_name
        print("reply:", response.query_result.fulfillment_text)
        
        if intent == '雷達回波圖':           # 如果是雷達回波圖相關的文字
            # 傳送雷達回波圖 ( 加上時間戳記 )
            reply_image('https://cwaopendata.s3.ap-northeast-1.amazonaws.com/Observation/O-A0058-001.png', reply_token, access_token)
        elif intent == '地震':              # 如果是地震相關的文字
            msg = earth_quake()                               # 爬取地震資訊
            push_message(msg[0], user_id, access_token)       # 傳送地震資訊 ( 用 push 方法，因為 reply 只能用一次 )
            reply_image(msg[1], reply_token, access_token)    # 傳送地震圖片 ( 用 reply 方法 )
        else:
            push_message(response.query_result.fulfillment_text, user_id, access_token)
    except:
        return 'error'

app = Flask(__name__)

@app.route("/", methods=['POST'])
def linebot():
    body = request.get_data(as_text=True)                    # 取得收到的訊息內容
    try:
        json_data = json.loads(body) 
        print(body)                        # json 格式化訊息內容
        access_token = 'Gs2gpzDO1/T99ggBEf/NqZfVjjejQ2zDL6iIJciH7MqqMVKkZAhNQL02P/SXx0t/LTkb9o7G0/bjQejhdpPiGdd1HGnhnEEISokwIFikKTYowZFJe0frqjvfJPIeOf+vwvZ/StynJASjIZQCnyt/NwdB04t89/1O/w1cDnyilFU='
        secret = '8de70cc350dc45902920777a64d73df8'
        line_bot_api = LineBotApi(access_token)              # 確認 token 是否正確
        handler = WebhookHandler(secret)                     # 確認 secret 是否正確
        signature = request.headers['X-Line-Signature']      # 加入回傳的 headers
        handler.handle(body, signature)                      # 綁定訊息回傳的相關資訊
        reply_token = json_data['events'][0]['replyToken']   # 取得回傳訊息的 Token
        user_id = json_data['events'][0]['source']['userId'] # 取得使用者 ID ( push message 使用 )
        type = json_data['events'][0]['message']['type']     # 取得 LINe 收到的訊息類型
        if json_data['events'][0]['message']['type'] == 'location':
            address = json_data['events'][0]['message']['address'].replace('台','臺')
            # 回覆爬取到的相關氣象資訊
            reply_message(f'{address}\n\n{current_weather(address)}\n\n{aqi(address)}\n\n{forecast(address)}', reply_token, access_token)
            print(address)
        elif type=='text':
            msg = json_data['events'][0]['message']['text']      # 取得 LINE 收到的文字訊息
            print(msg)                                           # 印出內容
            dialogflowFn(msg,reply_token,access_token,user_id)   # dialogflow 處理後回傳文字
        #    
        # elif type=='image':
        #     msgID = json_data['events'][0]['message']['id']
        #     message_content = line_bot_api.get_message_content(msgID)
        #     with open(f'{msgID}.jpg', 'wb') as fd:
        #         fd.write(message_content.content)
            # res = requests.put(
            #     headers={
            #         "Accept": "application/vnd.github+json",
            #         "Authorization": f"Bearer {os.getenv('GITHUB')}"
            #     },
            #     json={
            #         "message": f"✨ Commit",
            #         "committer": {"name": "chanaaaaaaa", "email": os.getenv('king960129@gmail.com')},
            #         "content": f"{base64.b64encode(message_content).decode('ascii')}",
            #         "branch": "main"},
            #     url=f"https://github.com/chanaaaaaaa/line-bot/blob/main/image/qrcode.png"
            # )

            # print(res.status_code)
            # print(res.json())
        else:
            reply = '我看不懂～'
            print(reply)
            line_bot_api.reply_message(reply_token,TextSendMessage(reply))# 回傳訊息
    except:
        print(body)                                          # 如果發生錯誤，印出收到的內容
    return 'OK'                                              # 驗證 Webhook 使用，不能省略

if __name__ == "__main__":
    app.run()