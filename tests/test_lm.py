# -*- coding: utf-8 -*-
import requests

url = "http://192.168.3.118:1234/v1/chat/completions"

payload = {
    "messages": [
        {"role": "user", "content": "Hola, ¿funciona?"}
    ],
    "temperature": 0.7,
    "max_tokens": 50
}

response = requests.post(url, json=payload)
print(response.json()['choices'][0]['message']['content'])