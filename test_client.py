import asyncio

from fastmcp import Client


async def test_server():
    client = Client("http://localhost:8000/mcp")

    async with client:
        result = await client.call_tool("get_recent_commits", {"count": 5})
        print("Recent commits:")
        print(result)

if __name__ == "__main__":
    asyncio.run(test_server())
