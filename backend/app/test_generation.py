import asyncio
from app.services.kie_client import KieClient

async def main():
    client = KieClient()
    res = await client.generate_images(prompts=["a lovely dog"], model="nano-banana-pro")
    print(res)

if __name__ == "__main__":
    asyncio.run(main())
