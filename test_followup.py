import asyncio
from app import process_query

async def test_followup():
    user_id = "FOLLOWUP_TEST_USER"
    # 1. First question
    print("Q1: Intel Xeon W-2400 คืออะไร?")
    ans1 = await process_query(user_id, "Intel Xeon W-2400 คืออะไร?")
    print(f"A1: {ans1[:100]}...")
    
    # 2. Follow-up
    print("\nQ2: มีจุดเด่นยังไงบ้าง?")
    ans2 = await process_query(user_id, "มีจุดเด่นยังไงบ้าง?")
    print(f"A2: {ans2[:100]}...")

if __name__ == "__main__":
    asyncio.run(test_followup())
