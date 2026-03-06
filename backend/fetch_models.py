import os
import urllib.request
import json
import ssl

ssl_context = ssl._create_unverified_context()
api_key = os.getenv("KIE_API_KEY")
if not api_key:
    raise SystemExit("Missing KIE_API_KEY env var")
req = urllib.request.Request("https://api.kie.ai/v1/models", headers={"Authorization": f"Bearer {api_key}"})
try:
    with urllib.request.urlopen(req, context=ssl_context) as response:
        print(response.status)
        print(response.read().decode('utf-8'))
except Exception as e:
    print(f"Error: {e}")
    read_fn = getattr(e, "read", None)
    if callable(read_fn):
        data = read_fn()
        if isinstance(data, bytes):
            print(data.decode("utf-8"))
        else:
            print(str(data))
