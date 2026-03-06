import urllib.request
import json
import ssl

ssl_context = ssl._create_unverified_context()
req = urllib.request.Request("https://api.kie.ai/v1/models", headers={"Authorization": "Bearer REDACTED"})
try:
    with urllib.request.urlopen(req, context=ssl_context) as response:
        print(response.status)
        print(response.read().decode('utf-8'))
except Exception as e:
    print(f"Error: {e}")
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8'))
