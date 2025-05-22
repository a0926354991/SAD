import requests

API_KEY = "AIzaSyA_XdPaEX51DHT-IbrQC8E3wDmgjDltB48"
search_keyword = "星巴克 台北101"
url = f"https://maps.googleapis.com/maps/api/place/findplacefromtext/json?input={search_keyword}&inputtype=textquery&fields=place_id,name,formatted_address&key={API_KEY}"

response = requests.get(url)
data = response.json()

if data["status"] == "OK":
    place = data["candidates"][0]
    place_id = place["place_id"]
    print(f"店名: {place['name']}, 地址: {place['formatted_address']}, Place ID: {place_id}")
else:
    print("找不到該地點！")
    print(f"{place['name']} - {place['vicinity']}")


PLACE_ID = "ChIJUzoMxrarQjQR_T4HJVWbE-I"

url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={PLACE_ID}&fields=name,reviews&language=zh-TW&key={API_KEY}"

response = requests.get(url)
data = response.json()

if data["status"] == "OK":
    place_details = data["result"]
    print(f"店名: {place_details['name']}")
    reviews = place_details.get("reviews", [])
    
    if reviews:
        for idx, review in enumerate(reviews, start=1):
            author = review["author_name"]
            rating = review["rating"]
            text = review["text"]
            time = review["relative_time_description"]
            print(f"\n第 {idx} 則評論")
            print(f"評論者: {author}")
            print(f"評分: {rating}")
            print(f"時間: {time}")
            print(f"內容: {text}")
    else:
        print("沒有評論。")
else:
    print("無法取得詳細資訊。")