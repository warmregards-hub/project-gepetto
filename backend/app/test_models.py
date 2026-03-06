import asyncio
import json
from app.services.kie_client import KieClient

async def main():
    client = KieClient()
    res = await client.list_models(kind="chat")
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
