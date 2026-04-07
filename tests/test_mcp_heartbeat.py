import asyncio
from src.interfaces.mcp_server import heartbeat

async def test_heartbeat():
    result = await heartbeat()
    print(f"Heartbeat Result: {result}")

if __name__ == "__main__":
    asyncio.run(test_heartbeat())
