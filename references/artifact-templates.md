# Artifact Templates & Quality Standards

เอกสารอ้างอิงรวบรวมโครงสร้างไฟล์สถานะระหว่างการพัฒนา (Continuous State Artifacts) และตารางตรวจสอบคุณภาพก่อนส่งมอบ (Scorecards) ที่จัดเก็บอย่างเป็นระเบียบในโฟลเดอร์ `.pipeline/`

---

## 1. โครงสร้าง `CHECKPOINT.json` (State Machine & Gate Control)

ใช้ควบคุมสถานะการพัฒนา บันทึกหลักฐานการตัดสินใจของมนุษย์ และป้องกันการข้ามขั้นตอน:

```json
{
  "schema_version": 2,
  "project_name": "earth-climate-monitor",
  "current_step": "3.0",
  "gates": {
    "G1": {
      "status": "APPROVED",
      "evidence": "User approved Architecture and ADR-001 to ADR-004 in chat 2026-11-12",
      "updated_at": "2026-11-12T13:08:25Z"
    },
    "G2": {
      "status": "PENDING",
      "evidence": null,
      "updated_at": "2026-11-12T13:10:30Z"
    },
    "G3": {
      "status": "NOT_REQUESTED",
      "evidence": null,
      "updated_at": "2026-11-12T13:10:30Z"
    }
  },
  "selected_design": "Theme B: Obsidian Minimal Luxury",
  "history": [
    {
      "action": "INIT",
      "step": "1.0",
      "evidence": "Pipeline initialized",
      "timestamp": "2026-11-12T12:58:00Z"
    },
    {
      "action": "APPROVE_GATE",
      "gate": "G1",
      "evidence": "User approved Architecture and ADR-001 to ADR-004 in chat",
      "timestamp": "2026-11-12T13:08:25Z"
    }
  ],
  "updated_at": "2026-11-12T13:10:30Z"
}
```

- **สถานะของ Gate ที่รองรับ:**
  - `NOT_REQUESTED`: ยังมาไม่ถึง Gate นี้
  - `PENDING`: กำลังหยุดรอคำตัดสินใจและหลักฐานอนุมัติจากผู้ใช้
  - `APPROVED`: ได้รับการอนุมัติอย่างเป็นทางการจากผู้ใช้ พร้อมบันทึกข้อความหลักฐานในฟิลด์ `evidence`
  - `WAIVED`: ได้รับการยกเว้นขั้นตอนอย่างมีเหตุผลทางเทคนิค (เช่น งาน Backend/CLI ไม่มี UI จึงยกเว้น G2)

---

## 1b. โครงสร้าง `.pipeline/PROJECT_STATE.md` (สถานะภาพรวมและภาษาเอกสาร)

```markdown
# ภาพรวมสถานะโครงการ (Project State)

## 1. ข้อมูลโครงการ & นโยบายภาษาเอกสาร (Project Info & Language Protocol)
- **ชื่อโครงการ (Project Name):** [ระบุชื่อระบบ เช่น Earth Climate Monitor]
- **เป้าหมายหลัก (Core Objective):** [อธิบายวัตถุประสงค์สั้นกระชับ 1-2 ย่อหน้า]
- **ภาษาของเอกสาร (Documentation Language):** [ภาษาไทย / English / สองภาษา (Bilingual)]
  > *หมายเหตุ: บันทึกจากการถามผู้ใช้ในขั้นที่ 1.0 และใช้ภาษานี้อย่างเคร่งครัดและสม่ำเสมอกับเอกสาร .md ทุกไฟล์ในโครงการ*
- **สถานะขั้นตอนปัจจุบัน (Current Step):** [เช่น 1.0 (Intake) / 2.0 (Spec & ADR)]
- **Tech Stack ที่เลือก:** [เช่น Node.js + SQLite (Zero-Dependency) หรือ In-Memory Adapter]

## 2. สรุปสถานะ Gate Locks (Human Approval Gates)
- **Gate G1 (Architecture & Spec Approval):** [NOT_REQUESTED / PENDING / APPROVED]
- **Gate G2 (Visual Direction & Design Selection):** [NOT_REQUESTED / PENDING / APPROVED / WAIVED]
- **Gate G3 (Multi-Role Production Delivery Sign-off):** [NOT_REQUESTED / PENDING / APPROVED]

## 3. ขอบเขตความต้องการหลัก (Key Functional Requirements)
1. [Requirement 1]
2. [Requirement 2]
3. [Requirement 3]

## 4. ข้อกำหนดที่อยู่นอกขอบเขต (Non-Goals & Out of Scope)
- [ข้อกำหนดที่ตัดออกหรือยังไม่ทำในเฟสนี้]
```

---

## 2. โครงสร้าง `Visual Direction & Design System Audit Report` (แสดงในแชทที่ขั้นที่ 3.0)

```markdown
### 🎨 รายงานตรวจสอบคุณภาพการออกแบบ UX/UI (Visual Direction & Design System Audit)
- **ดินแดนศิลปะที่เลือก (Chosen Anchor):** [Swiss / Industrial / Brutalist / Retro-Futuristic / Aurora / Organic / Lo-Fi / Chaotic]
- **อัตลักษณ์เฉพาะตัว (Differentiator):** [ระบุลูกเล่น Layout, ท่วงท่า Typography, หรือ Material Treatment เฉพาะตัวอย่างน้อย 1 อย่าง]
- **ระบบ 3-Tier Design Tokens:**
  - *Primitive Tokens:* [ค่าสีดิบ, ฟอนต์หลัก/รอง, สเกล Spacing 4px/8px]
  - *Semantic Tokens:* [การแมปสีพื้นหลัง, สีตัวอักษร, และสีขอบตามบทบาท]
  - *Component Tokens:* [ค่าตัวแปรเฉพาะปุ่ม, การ์ด, อินพุต]
- **วินัยด้านเนื้อหา (Content Discipline Check):** ผ่านเกณฑ์ 100% (ไร้ข้อมูล telemetry ปลอม, ไร้ subtitle ขยะ, ใช้ copy มาตรฐาน, ใช้ Inline SVG แทน Emoji, และตัดสำนวน AI Cliché ทั้งหมด)
- **การเข้าถึงและสถานะ (Accessibility & States):** คอนทราสต์ผ่าน WCAG AA ขั้นต่ำ 4.5:1, มีสถานะ Hover/Active/Focus-visible ครบทุกคอนโทรล, รองรับ Mobile Touch Target 44x44px
- **2 แนวทางการออกแบบสำหรับเลือกใช้งาน:**
  - **แนวทาง A ([ชื่อแนวทาง/Anchor]):** [อธิบายอารมณ์ โทนสี และกลุ่มผู้ใช้งานเป้าหมาย]
  - **แนวทาง B ([ชื่อแนวทาง/Anchor]):** [อธิบายอารมณ์ โทนสี และกลุ่มผู้ใช้งานเป้าหมาย]
```

---

## 2b. โครงสร้าง `.pipeline/DESIGN_SYSTEM.md` (จัดเก็บในขั้นตอนที่ 3.0)

```markdown
# Design System Architecture

## 1. Visual Direction & Anchor Selection
- **Product Type & Audience:** [e.g. B2B Analytics Dashboard for Engineers]
- **Theme A:** [Anchor name e.g. Industrial]
  - *Differentiator:* [e.g. Single semantic signal green, tabular numeric displays]
- **Theme B:** [Anchor name e.g. Aurora]
  - *Differentiator:* [e.g. Deep dark gradient mesh with glassmorphism surface]

## 2. 3-Tier Design Tokens
### Tier 1: Primitive Tokens
- `--color-slate-900: #0f172a;`
- `--font-sans: 'Inter', sans-serif;`
- `--font-mono: 'JetBrains Mono', monospace;`
- `--space-unit: 4px;`

### Tier 2: Semantic Tokens
- `--color-bg-surface: ...;`
- `--color-text-main: ...;`
- `--color-accent: ...;`
- `--color-border: ...;`

### Tier 3: Component Tokens
- `--button-primary-bg: ...;`
- `--card-padding: ...;`
- `--input-radius: ...;`

## 3. Harmonic Scales & Interaction
- **Typography Scale:** [e.g. 1.25 Major Third Scale]
- **Spacing Scale:** [4px, 8px, 16px, 24px, 32px, 48px]
- **Interactive States:** Default, Hover, Active, Focus-visible, Disabled ครบถ้วน
```

---

## 3. โครงสร้าง `REVIEW_GATE.md` (ใช้ในขั้นที่ 6.5)

```markdown
# รายงานการตรวจรับคุณภาพระบบก่อนส่งมอบ (Multi-Role Review Gate)

## 1. ผลการตรวจแยกตาม 6 บทบาท
- **1. System Architect:** [PASS/FAIL] ตรวจสอบการแยก Domain และ Adapter ตามสถาปัตยกรรม MVA รันเทสท์แบบ Offline ได้ 100% โดยไม่ต้องพึ่งพา Docker บนเครื่องพัฒนา
- **2. Lead Developer:** [PASS/FAIL] ตรวจสอบความสะอาดของโค้ด สอดคล้องตาม Spec และ Clean Code
- **3. QA & Reliability Engineer:** [PASS/FAIL] ตรวจสอบผลการรันชุดทดสอบอัตโนมัติครบถ้วน 100% ทั้ง Unit, Integration และ Edge Cases
- **4. Security Auditor:** [PASS/FAIL] ผลการรัน `scripts/security_audit.py` ผ่านเกณฑ์ ไม่พบ Hardcoded Secrets และช่องโหว่ OWASP
- **5. UX/UI & Usability Auditor:** [PASS/FAIL] ผลการตรวจ Visual Direction (Anchor Fidelity), 3-Tier Design Tokens และ Content Discipline
- **6. Orchestrator Verdict:** [APPROVED_FOR_DELIVERY / REJECTED]

## 2. ตารางตรวจสอบ Visual Direction & Design System Scorecard
| หัวข้อตรวจสอบ | เกณฑ์มาตรฐาน | สถานะ |
| :--- | :--- | :---: |
| 1. Aesthetic Anchor Fidelity | ยึดมั่นใน 1 Anchor ตาม CSS Tokens ไม่ผสมข้ามสายพันธุ์ | PASS |
| 2. Distinctive Differentiator | มีลูกเล่นที่เป็นเอกลักษณ์เฉพาะตัวอย่างน้อย 1 อย่างชัดเจน | PASS |
| 3. 3-Tier Tokens Architecture | จัดการตัวแปร CSS แยก Primitive, Semantic, Component เป็นระบบ | PASS |
| 4. Content Discipline (No Fake Data) | ไม่สร้างข้อมูล Telemetry หลอก หรือ Session ปลอมเพื่อประดับหน้า | PASS |
| 5. Clean UI Copy & No Filler Labels | ใช้ Copy มาตรฐานสำหรับ Action ตัด Subtitle ขยะและ AI Cliché | PASS |
| 6. Real Inline SVG Icons | ใช้ Inline SVG ที่มี aria-hidden ไม่ใช้อีโมจิหรือ Unicode glyphs | PASS |
| 7. Complete Interactive States | รองรับ Default, Hover, Active, Focus-visible, Disabled ครบ | PASS |
| 8. WCAG AA Contrast | ความต่างสีตัวอักษรกับพื้นหลังผ่านเกณฑ์อย่างน้อย 4.5:1 | PASS |
| 9. Responsive & Touch Targets | พื้นที่สัมผัสบน Mobile ขั้นต่ำ 44x44px พร้อม Meta Viewport | PASS |
| 10. Harmonic Scales | สเกล Spacing, Radius, Typography สอดคล้องกันทั้งระบบ | PASS |
| 11. Zero-Docker Local Verification | รันทดสอบในเครื่องผ่านได้ 100% Offline | PASS |
| 12. Complete Traceable Audit Trail | บันทึกประวัติและหลักฐานการตัดสินใจครบถ้วนใน `.pipeline/` | PASS |
```
