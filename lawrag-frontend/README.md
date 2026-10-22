# LawPilot AI — Exact Reference Website Recreation

> High-fidelity, reference-driven recreation of the [Astra Law Firm 04 Template](https://websitedemos.net/law-firm-04/?customize=template) adapted for **LawPilot AI** — an Agentic RAG-powered Legal Research System for Indian Legal Documents.

---

## 1. Primary Objective & Design Source of Truth

This frontend is an exact recreation of the reference website:
- **Reference URL**: `https://websitedemos.net/law-firm-04/?customize=template`
- **Design System**: Classic Legal Elegance (Serif headings, clean sans-serif body, refined gold accents, sharp button geometry, layered photographic sections with dark overlays).
- **Core Typography**:
  - Headings: `Playfair Display` (Serif, 700 / 600 weight)
  - Body & UI: `Raleway` (Sans-Serif, 500 / 600 / 700 weight)
  - Code & Citations: `JetBrains Mono`
- **Color Palette**:
  - Primary Gold Accent: `#e3b969`
  - Highlighted Card Gold Tint: `#ead181`
  - Deep Navy: `#00123a`
  - Warm Sand Background: `#f9f7f3`
  - Pure White: `#ffffff`
  - Dark Charcoal / Black: `#111111` / `#000000`

---

## 2. Section-by-Section Recreation Mapping

| Reference Section | LawPilot AI Recreation | Visual Elements & Behavior |
| :--- | :--- | :--- |
| **A. Header & Navigation** | LawPilot AI Navigation | Translucent header with custom vector scales mark, navigation links (Home, About, Legal Research, How It Works, AI Agents, Contact), and outlined gold button `Start Legal Research`. Sticky backdrop blur on scroll. Mobile drawer for small viewports. |
| **B. Hero Section** | Legal Research Hero | Dark photographic background (`hero-bg.jpg`) with 75% black overlay. H1: *"Legal Research. Backed by Evidence."*, 50px gold divider, supporting copy, primary CTA button, secondary *"Explore How It Works"* button, and right-hand glass spec card. |
| **C. About Section** | Legal Research, Made Clearer | 2-column layout on `#f9f7f3` background. Left: H2 Playfair, 50px gold divider, platform description, authentic legal seal watermark, and founder/engine tag. Right: Overlapping portrait photo (`about-img.jpg`). |
| **D. Practice Areas** | Supported Legal Research Categories | Identical grid: Row 1 with 4 cards (`.01` Employment & Labour, `.02` Commercial & Contracts, `.03` Consumer Protection, `.04` Property Law). Row 2 with 2 cards (`.05` Constitutional Law, `.06` Criminal Law) plus the signature warm gold highlighted card (`#ead181`) with bullet points and CTA. Clicking any category opens research pre-filtered. |
| **E. Why Choose Us / FAQ** | How LawPilot AI Works | Courtroom background (`courtroom-bg.jpg`) with 68% dark overlay. Left: Title and Hallucination Guardrail badge. Right: 5-item interactive accordion with gold active state answering information retrieval, citation display, insufficient evidence, precedent comparison, and disclaimer boundaries. |
| **F. Statistics Strip** | System & Corpus Statistics | Floating 5-column white card overlapping the courtroom section with drop-shadow. Real metrics: 24,500+ Indexed Judgments, 185K+ Searchable Chunks, 4 Autonomous Agents, 6 Disciplines, 100% Source Traceability. |
| **G. Testimonials / Trust** | Research Integrity & Verifiable Truth | Split background (66% warm sand `#f9f7f3` / 34% white). Giant quote icon, evidentiary grounding statement, protocol avatar, 5 gold stars, and 4 institutional repository cards (Supreme Court of India, Central Acts, High Courts, Zero-Hallucination Guard). |
| **H. Attorneys Grid** | Autonomous Research Agents | 4 profile cards matching the exact reference portrait layout (235x350 aspect ratio), top borders, titles, roles, and capability summaries: Legal Query Planner, Retrieval Agent, Evidence Verification Agent, Answer Synthesis Agent. |
| **I. Final Call to Action** | Research with Greater Clarity | Deep navy `#00123a` background, centered 50px gold divider, H2 Playfair, and primary CTA button. |
| **J. Footer** | 3-Tier Astra Footer | Tier 1: Legal assistance callout. Tier 2: 3 columns (Corpus Registry, System Status & API, Legal Operations). Tier 3: Copyright, Privacy Policy, and Responsible AI Legal Disclaimer modal. |

---

## 3. Working Legal Research Application (Section 7)

Accessible by clicking any **"Start Legal Research"** button or category chip:
1. **Legal Question Input**: Textarea for natural language legal questions.
2. **Category Filter**: Domain selector (Employment & Labour, Contracts, Consumer, Property, Constitutional, Criminal).
3. **One-Click Pre-Grounded Queries**:
   - Termination & Retrenchment compliance under Section 25F (Industrial Disputes Act, 1947).
   - Patent Illegality grounds to set aside domestic arbitral awards under Section 34 (Arbitration Act, 1996).
   - Flat buyer delayed possession remedies under Consumer Protection Act, 2019.
   - High Court inherent powers under Section 482 CrPC / Section 528 BNSS to quash FIRs in civil disputes.
   - Continuous readiness and willingness under Section 16(c) of Specific Relief Act, 1963.
   - **⚠️ Explicit Insufficient Evidence Guard Test**: Tests system boundaries on uncorroborated queries, displaying the amber limitation notice.
4. **Autonomous Agent Progress Stepper**: Real-time visual progress through the 4 stages:
   - Stage 1: Query Planner
   - Stage 2: Retrieval Agent
   - Stage 3: Evidence Verification Agent
   - Stage 4: Answer Synthesis Agent
5. **Structured Research Output**:
   - Legal summary & ratio decidendi.
   - Tagged statutory provisions and sections.
   - Expandable precedent passages with Case Name, Court, Bench, Year, Reporter Citation (AIR/SCC), and paragraph quote.
   - Copy Memorandum and Ask Another Question actions.
   - Live backend status indicator showing connected FastAPI server or local ChromaDB fixture mode.

---

## 4. Environment Variables Configuration

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Key environment variables:
```ini
VITE_API_BASE_URL=http://localhost:8000
VITE_API_RESEARCH_ENDPOINT=/api/v1/research
VITE_API_HEALTH_ENDPOINT=/api/v1/health
VITE_ENABLE_MOCK_FALLBACK=true
VITE_DEFAULT_CORPUS=Indian Supreme Court & High Courts
```

---

## 5. Local Development & Build

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build production bundle
npm run build

# Preview production build
npm run preview
```

---

## 6. Deployment Guides

### Frontend Deployment (Vercel)
The repository includes `vercel.json` configured for single-page application rewrites:
```bash
# Deploy to Vercel via CLI
npx vercel --prod
```
Or import the GitHub repository in the Vercel dashboard:
- **Framework Preset**: Vite
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Environment Variables**: Add `VITE_API_BASE_URL` pointing to your deployed Render FastAPI backend URL.

### Backend Deployment (Render)
If deploying the accompanying FastAPI backend to Render:
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port 10000`
- Set `CORS_ORIGINS` to include your Vercel frontend domain (e.g. `https://lawpilot-ai.vercel.app`).
