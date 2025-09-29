import requests

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

url = "https://lemanapro.ru/search/?q=перчатки%20хлопчатобумажные"
resp = requests.get(url, headers=headers)

print(f"Status code: {resp.status_code}")
print(resp.text[:1000])  # можно 1000, чтобы видеть больше содержимого
