# System Development Skill (Universal Edition)

มาตรฐานการพัฒนาระบบซอฟต์แวร์สากลแบบครบวงจร (Universal Full-Lifecycle Development Pipeline) ที่ออกแบบมาเพื่อรองรับ AI Coding Agent ทุกค่าย ทั้ง **OpenAI Codex/ChatGPT, Google Antigravity/Agy, Anthropic Claude Code, Cursor, Windsurf, Aider และ Roo Code**

---

## 🌟 จุดเด่นหลัก (Key Highlights)

1. **Evidence-Driven Gate Control (`scripts/pipeline_gate.py`)**:
   - ควบคุมการข้ามขั้นตอนด้วยระบบ Human Approval Gates (G1: Architecture, G2: Design, G3: Delivery)
   - บันทึกผู้อนุมัติ แหล่งอ้างอิง และรุ่นที่อนุมัติ พร้อมตรวจ SHA-256 ของไฟล์ที่ผูกกับ Gate
2. **Clean Repository Structure (`.pipeline/`)**:
   - จัดเก็บไฟล์สถานะและเอกสารตรวจสอบไว้ในโฟลเดอร์เฉพาะ `.pipeline/` ไม่กองรกที่ Root Directory ของโปรเจกต์
3. **Proportional Workflow (ยืดหยุ่นตามขนาดงาน)**:
   - งานใหญ่รันเต็มรูปแบบ 1.0 ถึง 7.0
   - งานแก้บั๊กเล็กสามารถทำแบบย่อและใช้คำสั่ง `waive` สำหรับ G2 เมื่อขอบเขตงานรุ่นนั้นไม่มี UI
4. **Zero-Docker Dev Policy**:
   - แยก Domain ด้วย Repository/Adapter Pattern พร้อม Mock Adapter ในตัว รันเทสท์ในเครื่องได้ 100% Offline ไม่ต้องเปิด Docker
5. **UI Prototype Engine & Design System (frontend-design + ui-ux-pro-max)**:
   - ออกแบบ UI Prototype (`preview.html`) ที่มี Multi-Theme Switcher ให้คลิกสลับเปรียบเทียบในหน้าเดียวอย่างน้อย 3 ถึง 4 ธีม (Theme A, B, C, D...) พร้อมสร้าง `.pipeline/DESIGN_SYSTEM.md` ผ่านการ Explicit Delegation ไปยัง `frontend-design` และ `ui-ux-pro-max` (หรือรัน Inline Deep Execution อัตโนมัติ) เพื่อคุณภาพงานระดับโปร ปราศจาก AI Slop 100%
6. **OWASP Security Scanner (`scripts/security_audit.py`)**:
   - สแกนหา Hardcoded Secrets และช่องโหว่ OWASP Top 10 พร้อมระบบ Redaction ซ่อนรหัสผ่านในผลรายงาน
7. **Production Verification (`scripts/verify_delivery.py`)**:
   - ส่งออกเฉพาะไฟล์ใน `release-files.txt` และเผยแพร่แพ็กเกจเมื่อผลตรวจโปรเจกต์และชุดชั่วคราวผ่าน
8. **Documentation Language Protocol**:
   - ถามความต้องการภาษาของเอกสาร Markdown (`.md`) ตั้งแต่ขั้นตอนที่ 1.0 (ไทย / English / Bilingual) เพื่อให้เอกสารทั้ง `.pipeline/` และ `README.md` มีภาษาที่สม่ำเสมอตรงใจผู้ใช้งาน

---

## 🚀 การติดตั้งและการใช้งาน (Installation & Usage)

### วิธีที่ 1: ติดตั้งผ่าน Agent Skills CLI (เร็วที่สุด)
สำหรับผู้ใช้ที่มีสิทธิ์เข้าถึง Private Repository:
```bash
npx skills add SnakeEyes288/system-development --skill system-development --global --yes
```

### วิธีที่ 2: ติดตั้งผ่าน Git Clone + Auto-Installer (รองรับทุกระบบปฏิบัติการ)
```bash
# 1. Clone repository ลงในเครื่อง
git clone https://github.com/SnakeEyes288/system-development.git
cd system-development

# 2. รันสคริปต์ติดตั้งอัตโนมัติ (จะคัดลอกไปยังโฟลเดอร์สกิลของ Agent ทุกค่ายในเครื่อง)
# บน Windows (PowerShell):
.\install.ps1

# บน macOS / Linux (Bash):
chmod +x install.sh && ./install.sh
```

### วิธีที่ 3: ติดตั้งด้วยตนเอง (Manual Copy)
คัดลอกโฟลเดอร์ `system-development` ไปวางในโฟลเดอร์ Agent ที่ต้องการ:
- **Google Antigravity (Agy):** `~/.gemini/config/skills/system-development`
- **Universal Agent Standard:** `~/.agents/skills/system-development`
- **Anthropic Claude Code:** `~/.claude/skills/system-development`
- **OpenAI Codex:** `~/.codex/skills/system-development`

---

### 💻 คำสั่งสคริปต์หลักสำหรับการพัฒนาระบบ
```bash
# 1. เริ่มต้นโปรเจกต์
python scripts/pipeline_gate.py init --project "My Project"

# 2. ดูสถานะและ Gate ปัจจุบัน
python scripts/pipeline_gate.py status

# 3. ขยับขั้นตอน (ต้องระบุ evidence)
python scripts/pipeline_gate.py advance --step 2.0 --evidence "Requirements verified"

# 4. ขออนุมัติ Gate
python scripts/pipeline_gate.py request --gate G1 --subject docs/SPEC.md

# 5. บันทึกการอนุมัติของมนุษย์
python scripts/pipeline_gate.py approve --gate G1 --revision "REVISION_FROM_REQUEST" --approver "Project owner" --evidence "Approval reference"

# 6. ขอยกเว้น Gate สำหรับงานที่ไม่มี UI
python scripts/pipeline_gate.py request --gate G2 --revision backend-scope-v1
python scripts/pipeline_gate.py waive --gate G2 --revision backend-scope-v1 --evidence "Backend API: no UI required"

# 7. สแกนความปลอดภัย OWASP
python scripts/security_audit.py .

# 8. ตรวจ checkpoint และส่งออกด้วย release-files.txt จาก root ของโปรเจกต์
python scripts/pipeline_gate.py validate
python scripts/verify_delivery.py . --export-release ./dist-package

# 9. รัน Unit Tests ของตัว Skill
python -m unittest discover -s tests -v
```

แทน `REVISION_FROM_REQUEST` ด้วยรุ่นที่คำสั่ง `request` แสดง และใช้คำอนุมัติจากแหล่งต้นทาง อ้างอิง [วิธีใช้ Gate และรายการไฟล์ส่งออก](SKILL.md) สำหรับการเปิดตรวจใหม่และการปรับจาก checkpoint schema 2
