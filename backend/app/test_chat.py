import asyncio
import json
from app.services.kie_client import KieClient

async def main():
    client = KieClient()
    res = await client.chat_completion([{"role": "user", "content": "hello"}])
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
