import asyncio
from database import test_connection

if __name__ == "__main__":
    asyncio.run(test_connection())