import requests
import json
token = requests.post(http://localhost:8000/api/auth/token, data={username:admin, password:password}).json().get(access_token)
if token:
    print(requests.post(http://localhost:8000/api/agent/chat, json={message: Generate
