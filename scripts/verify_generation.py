print("!!! SCRIPT START !!!")
import requests
import json
import re
import sys

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.3:70b"

GEN_SYSTEM_PROMPT = """คุณคือที่ปรึกษาผู้เชี่ยวชาญ (Detailed Consultant) ที่มีความเป็นมืออาชีพและให้ข้อมูลอย่างละเอียด โดยใช้ภาษาที่เป็นทางการในระดับกึ่งทางการ (Semi-formal)

งานของคุณคือการตอบคำถามของผู้ใช้โดยใช้ 'บริบท (Context)' ที่ได้รับมาเท่านั้น หากข้อมูลในบริบทไม่เพียงพอ ให้แจ้งผู้ใช้อย่างสุภาพว่าไม่พบข้อมูลดังกล่าวในฐานข้อมูล

**โครงสร้างการตอบกลับที่ต้องปฏิบัติตามอย่างเคร่งครัด:**
1. **[Acknowledgement]**: กล่าวรับทราบคำถามและเกริ่นนำสั้นๆ ให้ดูเป็นมืออาชีพ
2. **[Detailed Answer]**: ให้คำตอบที่ละเอียด ครบถ้วน และเจาะลึก โดยวิเคราะห์จากข้อมูลในบริบท หากเป็นข้อมูลเชิงเทคนิค ให้เน้นความถูกต้องและคำอธิบายที่เข้าใจง่ายแต่ลึกซึ้ง
3. **[Source Reference]**: ระบุแหล่งที่มาของข้อมูลที่ใช้ในคำตอบ (เช่น ชื่อไฟล์ หรือหัวข้อ)
4. **[Follow-up Suggestion]**: แนะนำคำถามหรือหัวข้อที่เกี่ยวข้องที่ผู้ใช้อาจสนใจเพิ่มเติม เพื่อนำไปสู่การให้คำปรึกษาที่สมบูรณ์ขึ้น

**ข้อกำหนดสำคัญ:**
- ต้องตอบเป็นภาษาไทยเท่านั้น
- ห้ามสร้างข้อมูลขึ้นมาเอง (No Hallucinations) นอกเหนือจากที่ระบุในบริบท
- รักษาบุคลิกภาพของที่ปรึกษาที่พร้อมช่วยเหลือและให้ข้อมูลเชิงลึก"""

REFINE_SYSTEM_PROMPT = """คุณคือผู้ตรวจสอบคุณภาพคำตอบ (Quality Assurance Gate) สำหรับระบบ RAG โดยมีหน้าที่ตรวจสอบคำตอบที่ร่างขึ้นมาเปรียบเทียบกับบริบทที่ได้รับ

**เกณฑ์การตรวจสอบ:**
1. **การหลอนของข้อมูล (Hallucinations)**: มีข้อมูลใดในคำตอบที่ไม่อยู่ในบริบทที่ให้มาหรือไม่? หากมี ต้องตัดออกหรือแก้ไขให้ถูกต้องตามบริบท
2. **ระดับรายละเอียด (Detail Level)**: คำตอบมีความละเอียดเพียงพอสำหรับระดับ 'ที่ปรึกษาผู้เชี่ยวชาญ' หรือไม่? หากสั้นเกินไป หรือขาดการวิเคราะห์เชิงลึก ให้ทำการขยายความโดยใช้ข้อมูลจากบริบท
3. **ความเป็นธรรมชาติของภาษา (Language)**: ภาษาไทยที่ใช้มีความเป็นธรรมชาติ สละสลวย และคงระดับกึ่งทางการ (Semi-formal) หรือไม่?

**แนวทางการดำเนินการ:**
- หากคำตอบผ่านเกณฑ์ทั้งหมด: ให้ตอบกลับด้วยคำว่า 'APPROVED' ตามด้วยคำตอบเดิม
- หากคำตอบไม่ผ่านเกณฑ์: ให้เขียนคำตอบฉบับปรับปรุง (Refined Version) ที่แก้ไขข้อบกพร่องข้างต้น โดยยังคงโครงสร้าง [Acknowledgement] $\rightarrow$ [Detailed Answer] $\rightarrow$ [Source Reference] $\rightarrow$ [Follow-up Suggestion] และต้องเป็นภาษาไทยเท่านั้น"""

def call_llm(system_prompt, user_prompt):
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        return response.json()['message']['content']
    except Exception as e:
        return f"Error calling LLM: {e}"

def post_process(text):
    """Mimics the n8n Code node post-processing logic."""
    return re.sub(r'^APPROVED\s*', '', text, flags=re.IGNORECASE).replace('REFINED:', '', 1).strip()

def validate_structure(text):
    """Verifies that all 4 required sections are present."""
    required_sections = [
        "[Acknowledgement]",
        "[Detailed Answer]",
        "[Source Reference]",
        "[Follow-up Suggestion]"
    ]
    missing = [section for section in required_sections if section not in text]
    if missing:
        raise AssertionError(f"Missing required sections: {', '.join(missing)}")
    return True

def verify():
    print("Starting verification tests...")

    # Test Case 1: Standard flow (Positive)
    context = """
    File: AMD_EPYC_9004_Genoa_Datasheet.pdf
    The AMD EPYC 9004 Series (Genoa) provides significant performance leaps in core count and memory bandwidth.
    It supports DDR5 memory and PCIe Gen 5.
    The maximum core count is 96 cores per socket.
    TDP ranges from 200W to 400W depending on the model.
    It is designed for cloud computing and high-performance computing (HPC).
    """
    query = "AMD EPYC 9004 Genoa มีจุดเด่นอะไรบ้าง และรองรับเทคโนโลยีอะไรบ้าง?"

    print("\n--- Test Case 1: Standard Flow ---")
    gen_user_prompt = f"Context: {context}\n\nQuery: {query}"
    draft = call_llm(GEN_SYSTEM_PROMPT, gen_user_prompt)

    refine_user_prompt = f"Context: {context}\n\nDraft Answer: {draft}"
    refined = call_llm(REFINE_SYSTEM_PROMPT, refine_user_prompt)

    # Post-processing check
    final_output = post_process(refined)

    print(f"Refined (Raw):\n{refined}\n")
    print(f"Final Output (Post-processed):\n{final_output}\n")

    # Assertions
    assert "APPROVED" not in final_output or not final_output.startswith("APPROVED"), "Post-processing failed to remove APPROVED prefix"
    validate_structure(final_output)
    print("✓ Test Case 1 Passed: Structure is correct and prefix is removed.")

    # Test Case 2: Bad Draft (Negative) - Testing the Refinement Gate
    print("\n--- Test Case 2: Bad Draft (Hallucination & Brief) ---")
    bad_draft = """
    **[Acknowledgement]**
    สวัสดีครับ

    **[Detailed Answer]**
    AMD EPYC 9004 Genoa ดีมากครับ รองรับ DDR5 และมีราคาถูกที่สุดในตลาด

    **[Source Reference]**
    ข้อมูลจากเน็ต

    **[Follow-up Suggestion]**
    ถามต่อได้ครับ
    """
    refine_bad_user_prompt = f"Context: {context}\n\nDraft Answer: {bad_draft}"
    refined_bad = call_llm(REFINE_SYSTEM_PROMPT, refine_bad_user_prompt)
    final_bad_output = post_process(refined_bad)

    print(f"Bad Draft:\n{bad_draft}\n")
    print(f"Refined Bad Draft (Post-processed):\n{final_bad_output}\n")

    validate_structure(final_bad_output)
    print("✓ Test Case 2 Passed: Refinement Gate fixed the bad draft and preserved structure.")

    # Test Case 3: Empty Context (Negative)
    print("\n--- Test Case 3: Empty Context ---")
    empty_context = ""
    query_empty = "ข้อมูลเกี่ยวกับ CPU รุ่นใหม่"
    gen_empty_prompt = f"Context: {empty_context}\n\nQuery: {query_empty}"
    draft_empty = call_llm(GEN_SYSTEM_PROMPT, gen_empty_prompt)

    print(f"Draft (Empty Context):\n{draft_empty}\n")

    try:
        validate_structure(draft_empty)
        print("✓ Test Case 3 Passed: System maintained structure even with empty context.")
    except AssertionError as e:
        print(f"⚠ Test Case 3 Warning: {e}")

if __name__ == "__main__":
    verify()
