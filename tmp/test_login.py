import requests, json, sys
url='http://localhost:8000/api/auth/token'
resp=requests.post(url, json={'username':'admin','password':'gepetto'})
print('Auth status', resp.status_code)
print('Auth body', resp.text)
if resp.status_code==200:
    token=resp.json()['access_token']
    chat_url='http://localhost:8000/api/agent/chat'
    chat_resp=requests.post(chat_url, headers={'Authorization': f'Bearer {token}'}, json={'message':'Hello, are you there?', 'project_id':'test'})
    print('Chat status', chat_resp.status_code)
    print('Chat body', chat_resp.text)
else:
    sys.exit(1)
