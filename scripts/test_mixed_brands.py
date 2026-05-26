import asyncio
import random
import time
import sys
import os

# Add current directory to path so we can import app
sys.path.append(os.getcwd())
from app import process_query

test_questions = [
    # Cloudera
    ("CLOUDERA", "Cloudera คืออะไร?"),
    ("CLOUDERA", "Cloudera รองรับ Oracle Cloud มั้ย?"),
    ("CLOUDERA", "Cloudera AI Overview ปี 2025 มีหัวข้อหลักอะไรบ้าง?"),
    ("CLOUDERA", "การออกแบบระบบ Cloudera ต้องใช้ CPU กี่คอร์?"),
    ("CLOUDERA", "Cloudera Manager คืออะไร?"),
    ("CLOUDERA", "ประโยชน์ของ Cloudera on OCI คืออะไร?"),
    ("CLOUDERA", "Cloudera ใช้ Hadoop เป็นพื้นฐานใช่หรือไม่?"),
    ("CLOUDERA", "Hardware spec ขั้นต่ำสำหรับ Cloudera คืออะไร?"),
    ("CLOUDERA", "Cloudera ต่างจากบริษัท Big Data อื่นอย่างไร?"),
    ("CLOUDERA", "มีเอกสาร Cloudera รุ่นปี 2023 มั้ย?"),

    # SAS
    ("SAS", "SAS Viya คืออะไร?"),
    ("SAS", "SAS มีนโยบาย Distributor อย่างไรในปี 2023?"),
    ("SAS", "SAS Analytics for manufacturing เน้นเรื่องอะไร?"),
    ("SAS", "SAS TOR สำหรับระบบวิเคราะห์ธุรกรรมทางการเงินเป็นของใคร?"),
    ("SAS", "SAS VSTECS มิถุนายน 2025 มีเนื้อหาเกี่ยวกับอะไร?"),
    ("SAS", "SAS ช่วยเรื่อง Intelligent decisioning อย่างไร?"),
    ("SAS", "SAS รองรับ Machine Learning และ Deep Learning มั้ย?"),
    ("SAS", "SAS มีเทคโนโลยี In-database อะไรบ้าง?"),
    ("SAS", "SAS ช่วยเรื่อง Data Governance อย่างไร?"),
    ("SAS", "ใครคือ SAS ในมุมมองของอุตสาหกรรมการผลิต?"),

    # Infinitix
    ("INFINITIX", "Infinitix AI Stack คืออะไร?"),
    ("INFINITIX", "Infinitix มี PriceBook ปี 2025 มั้ย?"),
    ("INFINITIX", "AI Stack รองรับ GPU รุ่นไหนบ้าง (GPU Tier Support)?"),
    ("INFINITIX", "TOR ภาษาไทยของ AI-Stack มีรายละเอียดสำคัญอะไร?"),
    ("INFINITIX", "AI-Stack และ NVAIE มีความเกี่ยวข้องกันอย่างไร?"),
    ("INFINITIX", "Infinitix Pre-sales Global เน้นบริการอะไร?"),
    ("INFINITIX", "AI Stack Technical Specifications มีอะไรบ้าง?"),
    ("INFINITIX", "Infinitix ช่วยออกแบบ TOR ได้มั้ย?"),
    ("INFINITIX", "AI-Stack ของ Infinitix ต่างจาก Stack อื่นยังไง?"),
    ("INFINITIX", "Infinitix มีนาคม 2025 มีการอัปเดตราคาใหม่มั้ย?"),

    # Nvidia
    ("NVIDIA", "NVIDIA H200 NVL มีจุดเด่นอะไร?"),
    ("NVIDIA", "DGX B300 ของ NVIDIA คืออะไร?"),
    ("NVIDIA", "Jetson Orin มีรุ่นอะไรบ้าง?"),
    ("NVIDIA", "Aetina AI-MXM-H84A มีสเปกคร่าวๆ อย่างไร?"),
    ("NVIDIA", "DGX Spark คืออะไร?"),
    ("NVIDIA", "AIP-CR68-A1 ของ Aetina คืออะไร?"),
    ("NVIDIA", "NVIDIA GTC Updates เมษายน 2025 ในไทยมีอะไรน่าสนใจ?"),
    ("NVIDIA", "Jetson Orin Nano ต่างจาก Orin NX ยังไง?"),
    ("NVIDIA", "h200-nvl datasheet บอกอะไรบ้าง?"),
    ("NVIDIA", "NVIDIA ช่วยเรื่อง AI Infrastructure อย่างไร?")
]

async def run_test():
    user_id = "test_user_mixed_brands_" + str(random.randint(1000, 9999))
    print(f"Starting Brand-Switch Test for user: {user_id}")

    # Shuffle questions to create random brand switching
    random.shuffle(test_questions)

    # Select a subset to avoid taking too long, but enough to test switching
    selected_tests = test_questions[:15]

    for i, (brand, question) in enumerate(selected_tests):
        print(f"\n--- Turn {i+1} ---")
        print(f"[Expected Brand: {brand}] Question: {question}")

        start_time = time.time()
        try:
            answer = await process_query(user_id, question)
            elapsed = time.time() - start_time
            print(f"Bot Answer: {answer}")
            print(f"Time taken: {elapsed:.2f}s")
        except Exception as e:
            print(f"Error occurred: {e}")

    print("\n--- Test Complete ---")

if __name__ == "__main__":
    asyncio.run(run_test())
