import asyncio
import os
import sys
import random

# Add project root to path to import app
sys.path.append(os.getcwd())

from app import process_query

test_questions = [
    # Cloudera
    ("CLOUDERA", "Cloudera คืออะไร?"),
    ("CLOUDERA", "Cloudera รองรับ Oracle Cloud มั้ย?"),
    ("CLOUDERA", "การออกแบบระบบ Cloudera ต้องใช้ CPU กี่คอร์?"),
    ("CLOUDERA", "Cloudera Manager คืออะไร?"),
    ("CLOUDERA", "Cloudera ใช้ Hadoop เป็นพื้นฐานใช่หรือไม่?"),
    
    # SAS
    ("SAS", "SAS Viya คืออะไร?"),
    ("SAS", "SAS Presentation for INOAC มีเนื้อหาเกี่ยวกับอะไร?"),
    ("SAS", "SAS TOR สำหรับระบบวิเคราะห์ธุรกรรมทางการเงินเป็นของใคร?"),
    ("SAS", "SAS ช่วยเรื่อง Intelligent decisioning อย่างไร?"),
    ("SAS", "SAS มีเทคโนโลยี In-database อะไรบ้าง?"),
    
    # Infinitix
    ("INFINITIX", "Infinitix AI Stack คืออะไร?"),
    ("INFINITIX", "Infinitix มี PriceBook ปี 2025 มั้ย?"),
    ("INFINITIX", "AI Stack รองรับ GPU รุ่นไหนบ้าง?"),
    ("INFINITIX", "TOR ภาษาไทยของ AI-Stack มีรายละเอียดสำคัญอะไร?"),
    ("INFINITIX", "Infinitix ช่วยออกแบบ TOR ได้มั้ย?"),
    
    # Nvidia
    ("NVIDIA", "NVIDIA H200 NVL มีจุดเด่นอะไร?"),
    ("NVIDIA", "DGX Spark คืออะไร?"),
    ("NVIDIA", "Jetson Orin มีรุ่นอะไรบ้าง?"),
    ("NVIDIA", "Aetina AI-MXM-H84A มีสเปกคร่าวๆ อย่างไร?"),
    ("NVIDIA", "Thailand-GTCUpdates-April2025 มีอะไรใหม่บ้าง?")
]

random.shuffle(test_questions)

async def run_internal_test():
    user_id = "test_agent_sim"
    print(f"--- SIMULATED MULTI-BRAND TEST START ---\n")
    
    for i, (brand, q) in enumerate(test_questions):
        print(f"[{i+1}/20] BRAND: {brand}")
        print(f"QUERY: {q}")
        
        try:
            answer = await process_query(user_id, q)
            print(f"ANSWER: {answer}\n")
            print("-" * 50)
        except Exception as e:
            print(f"ERROR: {e}\n")
            
    print(f"\n--- TEST COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(run_internal_test())
