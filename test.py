import requests
import json

try:
    print("Logging in...")
    token = requests.post("http://localhost:8000/api/auth/token", data={"username":"admin", "password":"password"}).json().get("access_token")
    if token:
        print("Logged in, sending chat...")
        res = requests.post("http://localhost:8000/api/agent/chat", json={"message": "Generate dog using nano-banana-pro", "project_id": "test"}, headers={"Authorization": f"Bearer {token}"})
        print(res.status_code)
        print(res.text)
    else:
        print("No token")
except Exception as e:
    print(e)
