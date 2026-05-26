import asyncio
from app import process_query

async def test_fuzzy_greeting():
    print("Testing fuzzy greeting: 'สวสั ดี'")
    ans = await process_query("TEST_USER", "สวสั ดี")
    print(f"Response: {ans}")
    if "สวัสดีครับ" in ans:
        print("PASS: Fuzzy greeting matched")
    else:
        print("FAIL: Fuzzy greeting did not match")

if __name__ == "__main__":
    asyncio.run(test_fuzzy_greeting())
