# AI-Powered Scope of Work Manager (Buyout & Subcontract Tool)

> **Source**: PM_Automation.txt - Idea #33
> **Impact**: High
> **Complexity**: Medium (6-8 weeks typical; 6 weeks aggressive MVP)
> **Tags**: `#AI` `#NLP` `#construction` `#PM` `#buyout` `#subcontracts` `#scope` `#django` `#tool` `#collaboration`
> **Status**: Research
> **Started**: February 24, 2026
> **Last Updated**: March 3, 2026

---

## Executive Summary

**Problem**: General contractors build scope of work exhibits (Exhibit A) for every trade on every project — typically 10-30 trades per project. Today, PMs start from informal Word templates pulled from past projects on shared drives. There is no company-wide standardization; each PM maintains their own evolved versions with lessons learned baked in. A single scope exhibit for a larger trade takes 2-4 hours of dedicated work, and when 4-8 trades need to go out to bid simultaneously (often the day after receiving drawings), the math doesn't work. The result: scope exhibits go out incomplete or generic, relying on subcontractors to catch the full scope — which they don't always do. When drawings are vague and a sub interprets scope differently than the design intent, it leads to costly negotiations, wasted time, and change orders. Notes from team conversations, site walks, and coordination meetings get lost and resurface later as disputes.

**Solution**: An end-to-end scope of work management platform that covers the full buyout lifecycle — from template selection through subcontract Exhibit A. The full vision encompasses seven stages:

1. **Template Library & Customization** — Company-wide trade templates organized by CSI code, with ~60% reusable boilerplate (general conditions, standard inclusions/exclusions, schedule of values). The tool highlights sections needing project-specific review, replacing the current pattern of hunting through shared drives and past projects.

2. **AI-Assisted Scope Building** — Upload project specs (PDF) and the AI compares them against the template, flagging deviations in both directions: what's in the spec but not the template, and what's in the template but may not apply. An interactive Q&A session lets the PM add project-specific context (owner/architect conversations, design intent, incomplete drawing context) and the AI generates standardized inclusion/exclusion items.

3. **Notes & Comments Tracker** — Frictionless capture of scope-related notes from any team member (PM, PE, Superintendent). Notes tagged to primary trade + related trades. Handles open questions ("who's carrying the caulking?"), means & methods comments, and scope clarifications. Unresolved notes are tracked as open items that must be addressed before finalization.

4. **Cross-Trade Gap/Overlap Detection** — As scope exhibits are developed across all trades, AI analyzes scopes together to flag: scope gaps (work not assigned to any trade), scope overlaps (same work in multiple trades), and unresolved notes affecting multiple trades.

5. **Bid Recap Support** — Standardized framework for capturing subcontractor inclusions/exclusions during bid evaluation. Works alongside BuildingConnected exports (Google Sheets). Ensures consistent apples-to-apples comparison across 3-5 bidders per trade.

6. **Subcontract Conversion** — One-click conversion from bid exhibit to Exhibit A. Auto-converts language ("bidder" → "subcontractor"), incorporates bid clarifications, addenda, and resolved notes from the bidding period.

7. **TurboTax-Style Final Review** — Before issuing the subcontract, the system runs a completeness check: all notes resolved? Any scope gaps with adjacent trades? All bid clarifications incorporated? All open questions answered? Warns or blocks if issues remain.

Outputs PDFs — the standard format for sharing with subs and uploading to platforms (Procore, BuildingConnected). Teams use Bluebeam for markups and review. All editing happens inside the app. Scope exhibits are typically 1-10 pages per trade (1-2 pages project-specific, rest boilerplate).

> **MVP Focus**: Template management + AI scope language assistant (natural language → exhibit language) + notes tracker + final review checklist. AI spec reading from PDFs, gap detection, bid recap, and subcontract conversion are phased in as later features. The architecture should be designed from day one to support the full lifecycle.

**Why Now**: AI language models (Claude, GPT) are now capable enough to read construction specifications, compare them against scope templates, and flag deviations — something that required a human reading every spec section line by line. Combined with Django/Python document processing libraries, a solo developer with AI assistance can build what would have been a large team effort two years ago. Additionally, the owner has 12 years of construction PM experience and deeply understands the workflow, which is critical for getting the product right.

**Success Looks Like**: The PM team at Hathaway Dinwiddie uses this tool for every buyout. Scope exhibit creation drops from 2-4 hours per trade to under 1 hour. Templates are standardized company-wide and improve over time as lessons learned feed back in. Team notes are captured systematically and never lost. Scope gaps between trades are flagged before bid issuance, not discovered during construction.

---

## Target Users & Market Analysis

### Primary Users

**Persona 1: Project Manager (PM)** — Primary author and decision-maker
- Owns the buyout process and scope exhibit quality
- Selects templates, customizes scope, makes final calls on inclusions/exclusions
- Manages 3-5 concurrent projects, each with 10-30 trades to buy out
- Pain: Not enough hours to create thorough scope exhibits for every trade when 4-8 go out simultaneously

**Persona 2: Project Engineer (PE)** — Drafter and day-to-day user
- Drafts scope exhibits under PM direction, handles edits and revisions
- Enters notes from Superintendent and field conversations
- 1-2 PEs per project (more on larger projects)
- Pain: Repeating the same copy-paste-customize cycle from scattered Word templates with no standardization

**Persona 3: Estimator** — Early-stage user (preconstruction handoff)
- First to touch scope during preconstruction/estimating phase
- May handle buyout on some projects, especially when project team is not yet assigned
- Establishes initial scope assumptions that carry through to subcontract
- Pain: Scope assumptions made during estimating don't always transfer cleanly to the project team doing buyout

**Persona 4: Superintendent** — Indirect user (notes contributor)
- Provides means & methods input, constructability notes, logistics requirements
- Rarely uses the tool directly — PE or PM enters their notes
- Pain: Their input gets lost in hallway conversations and never makes it into the scope exhibit

**Typical project team**: 1 PM + 1-2 PEs. Larger projects: 1 Senior PM + 1-2 PMs with 2 PEs each. Estimators involved in preconstruction handoff and occasionally in buyout.

### Market Size

**Target: Mid-to-large commercial GCs in the US ($50M+ annual revenue)**

| Metric | Estimate | Source |
|--------|----------|--------|
| Commercial GC firms ($50M+) | 8,000-10,000 | Census Bureau NAICS 236220, Construction Benchmark Report |
| Project managers at these firms | 110,000-150,000 | BLS Construction Managers data |
| Commercial projects started/year | 50,000-75,000 | Dodge Construction Network |
| Annual commercial construction spending | $737B+ | St. Louis Fed |

**Per-project math**: 10-30 trades per project × 50,000-75,000 projects = **500,000 to 2.25 million scope exhibits created per year** across the industry. Each one currently done manually in Word.

**Initial target (Hathaway Dinwiddie)**: ~20+ PMs across the company, each managing multiple projects. Immediate internal user base of 50-100 PM/PE team members.

### Competition

**1. Procore / Autodesk Build / BuildingConnected**
- These platforms handle bid distribution, cost tracking, RFIs, submittals, and subcontract management
- **None of them create scope exhibits.** You create your Exhibit A in Word and upload it as an attachment
- They are workflow/document management platforms, not content creation tools

**2. Contexo AutoScopes** — *Closest in concept, but unproven*
- Claims to be "industry's first AI-powered" scope generation from project documents
- Trade-specific scope creation organized by CSI division
- Full preconstruction suite: also offers ITB, document management, planroom, estimating, submittals
- **Deep research findings (Feb 2026)**:
  - **Zero evidence of product-market fit**: No named customers, no case studies, no testimonials
  - **No reviews**: Nothing on G2, Capterra (listed but 0 reviews), or TrustRadius
  - **No press coverage**: Not mentioned in Construction Dive, ENR, or any trade publication
  - **No funding announcements**: No disclosed investors, no funding rounds
  - **No team visibility**: Founders, leadership, and employee count unknown
  - **No public demos**: No screenshots, videos, or product walkthroughs available
  - **Pricing hidden**: Enterprise-style "request demo" only
  - **Crozdesk score**: 42/100 (no user reviews backing it)
  - Virginia-based (703 area code)
- **Assessment**: Polished marketing website with heavy buzzwords but no substance. Could be very early stage or vaporware. The complete absence of any customer validation after claiming to be "industry's first" is a major red flag. Still worth taking a demo to see what they actually have.

**3. ConCntric** — *More credible AI preconstruction player*
- $10M Series A (Oct 2025), led by 53 Stations
- Named customers: Abbott Construction, Big-D Construction, Consigli Construction
- Product "Amplify": agentic AI for preconstruction — ingests project docs, generates dashboards/risk registers/reports
- Positioned as "not another estimating tool" — complements existing software
- **Not directly competing on scope exhibits**, but broader preconstruction AI that could expand into this space
- More credible threat long-term than Contexo

**4. Enterprise ERPs (CMiC, Viewpoint, Sage)**
- Financial/accounting focused. Track subcontracts and billing
- No scope creation capabilities — "attach your Word doc" approach

**5. Generic template tools (Sitemate, Smartsheet)**
- Digital forms, better than raw Word but still manual population
- No AI intelligence, no trade-specific knowledge, no learning from past projects

**6. DIY AI (ChatGPT + Word)**
- Any PM can use ChatGPT to help write scope language today
- No construction-specific training, no template libraries, no workflow integration, no collaboration
- "Good enough" for some, but not a real solution

**Bottom line**: After extensive research, **no direct competitor** is doing exactly what we described — a lightweight, template-driven, AI-assisted Exhibit A creation tool focused on the GC buyout workflow. Contexo is adjacent but positioned as enterprise preconstruction suite.

### Opportunity

**Why this gap exists**:
- Enterprise vendors (Procore, Autodesk) build workflow platforms, not content creation tools
- ERP systems (CMiC, Viewpoint) focus on accounting/financials
- AI startups (Contexo) target broad preconstruction automation at enterprise pricing
- Nobody is solving the specific PM pain point: "I need to create 15 Exhibit A documents this week and I'm copy-pasting from old Word files"

**Our unique angle**:
1. **Built by a PM, for PMs** — domain expertise that software companies lack
2. **Template-first approach** — GCs don't need AI to write scope from scratch. They already have boilerplate "legalese" that protects them — standard inclusions/exclusions, general conditions, reasonable assumption language, and change order provisions. These templates work. The problem isn't the content — it's the speed of customization, the lack of standardization across PMs, and the loss of lessons learned between projects. Starting from specs assumes specs are correct; starting from templates assumes the GC's institutional knowledge is the foundation (which it is). AI assists and enhances — it doesn't replace.
3. **Lightweight and focused** — solves buyout scope creation, doesn't try to be Procore
4. **Mid-market positioning** — affordable for regional GC teams, not enterprise-only
5. **Company knowledge compounds** — every project makes the templates better; lessons learned feed back into the system

**Contech investment context**: Built environment tech funding reached $4.4B in Q3 2025 (66% YoY increase), with 68% going to AI-based technologies. Investors are actively seeking scalable, data-driven construction AI solutions.

---

## Detailed Workflow / User Stories

### Context: The Buyout Lifecycle

A buyout starts with an **estimate** — a list of trades organized by CSI code, each with a budget. The PM works through these trades, creating scope exhibits (Exhibit A documents) to send to subcontractors for bidding. A typical project has 10-30 trades. On a busy week, 4-8 trades may need to go out simultaneously.

The lifecycle for a single trade:

```
Template Selection → Scope Customization → Notes Integration → Bid Issuance
    → Bid Evaluation → Subcontract Exhibit A → Final Review → Subcontract Issued
```

**MVP covers**: Template Selection, Scope Customization, Notes Integration, and Final Review.
**Later phases add**: AI spec reading (Stage 2), cross-trade gap detection (Stage 4), bid recap (Stage 5), subcontract conversion (Stage 6).

---

### Workflow 1: Project Setup & Trade List Import

**Who**: PM (once per project)

**Current process**: PM has an estimate spreadsheet with CSI codes and budgets. They mentally track which trades need scope exhibits and in what order (driven by schedule and bid timelines).

**New workflow**:

1. PM creates a new project in the tool (name, number, project type, address)
2. PM selects the **project type** from a predefined list:
   - Office Tenant Improvement (TI)
   - Lab / R&D Tenant Improvement
   - Core & Shell (new construction)
   - Seismic Retrofit
   - Mixed-Use
   - Other (custom)
3. PM imports or manually enters the trade list:
   - **Option A**: Paste/upload from estimate spreadsheet (CSI code + trade name + budget)
   - **Option B**: Select trades from a master CSI list and enter budgets manually
4. The tool creates a **buyout dashboard** showing all trades with status tracking:
   - Not Started
   - Scope In Progress
   - Out to Bid
   - Bids Received / Under Review
   - Subcontract Issued

**User Stories**:
- *As a PM, I want to create a project and import my trade list so I can see all trades I need to buy out in one place.*
- *As a PM, I want to tag my project type so the system recommends the most relevant templates for each trade.*
- *As a PM, I want to see a dashboard of all trades and their buyout status so I know what's done and what's outstanding.*

---

### Workflow 2: Template Selection & Scope Customization

**Who**: PM or PE (per trade)

**Current process**: PM goes to company shared drive or a past project folder. Searches for a scope exhibit from a similar project type. Copies the Word doc, renames it, and starts editing. The choice of which past project to pull from is based on project type similarity (e.g., for HVAC on a lab TI, pull from a previous lab TI project — not an office TI).

**New workflow**:

1. PM clicks into a trade (e.g., "231000 - HVAC") from the buyout dashboard
2. The tool shows **recommended templates**, ranked by relevance:
   - First: Company master template for that trade (if one exists)
   - Then: Past project scope exhibits for the same trade, filtered/sorted by project type match
   - Each template shows: source project name, project type, date created, who created it
3. PM selects a template. The tool loads it into the editor with two distinct zones:
   - **Boilerplate sections** (general conditions, standard inclusions/exclusions, schedule of values, BIM requirements, safety, cleanup, etc.)
   - **Project-specific sections** (quantities, areas, specific details, means & methods)
4. PM customizes the scope:
   - **Boilerplate**: Review and toggle sections on/off. Example: project doesn't require BIM coordination → uncheck/delete the BIM section. No LEED requirements → remove LEED section. Each boilerplate item is a discrete block that can be included or excluded.
   - **Project-specific**: Edit free-text sections with project details — quantities, areas, drawing references, spec section references, specific scope clarifications
5. PM can add **custom items** (inclusions or exclusions not in the template)
6. PM can view **unresolved notes** for this trade (see Workflow 3) directly in the scope editor
7. When ready, PM marks the scope as "Ready for Bid" and exports as PDF (primary format for sharing, attaching to bids, uploading to Procore/BuildingConnected). Teams use Bluebeam for markups and review.

#### AI Co-Pilot: Scope Language Assistant (MVP Feature)

Two AI-assisted capabilities are built into the scope editor from day one:

**A) Project/Trade Description → Exhibit Language**

When the PM starts working on a trade's scope, they can provide a **natural language description** of the project context and what this trade covers. The AI uses this to adapt the entire exhibit's tone, terminology, and project-specific sections.

*Example input*:
> "This is a 45,000 SF lab TI on floors 3 and 4 of an existing building. HVAC scope includes new VAV boxes, lab exhaust fans on the roof, fume hood connections, and extending the existing BMS controls. Existing AHUs stay — just modifying ductwork downstream."

*What the AI does*:
- Pre-populates Section 2 (Scope of Work) with exhibit-ready language: "Provide and install new Variable Air Volume (VAV) terminal units throughout floors 3 and 4, approximately 45,000 SF, per Drawings M2.1 through M2.4..."
- Generates initial Clarifications & Assumptions based on the description (e.g., "Existing AHUs to remain; no AHU replacement is included in this scope")

Generated items are inserted directly into the relevant sections of the exhibit. The PM then reviews and edits in place.

**Post-MVP enhancement**: The AI will also suggest relevant boilerplate toggles (e.g., auto-enables "BMS integration" and "lab exhaust" items, disables "new AHU installation") based on the scope description.

**B) Natural Language → Inclusion/Exclusion Items**

At any point while editing, the PM can type a scope item in plain language and the AI converts it to standardized exhibit language and adds it as an inclusion or exclusion block.

*Example inputs and outputs*:

| PM types (natural language) | AI generates (exhibit language) | Type |
|---|---|---|
| "sub needs to demo existing ceilings in rooms 201-215, keep grid in corridors" | "Demolition and removal of existing acoustical ceiling tile and grid in Rooms 201 through 215 per Drawing A2.1. Existing ceiling grid in corridors to remain; protect in place per Section 024119." | Inclusion |
| "we're not paying them for asbestos abatement" | "Asbestos abatement and remediation of hazardous materials is excluded from this scope of work. Abatement to be performed by Owner's separate contractor prior to commencement of work." | Exclusion |
| "they need to tie into the existing fire alarm panel in the basement" | "Connection and integration to existing fire alarm control panel (FACP) located in Basement Level B1. Provide all wiring, conduit, and programming required for new devices to communicate with existing system." | Inclusion |

The PM can edit the generated text before accepting it. Over time, the AI learns the company's preferred language patterns from accepted outputs.

**Why this works in MVP** (low implementation complexity):
- Straightforward Claude API calls with a well-crafted system prompt containing exhibit language conventions
- No PDF parsing, no spec comparison, no document ingestion — just text in, text out
- The system prompt includes: trade-specific terminology, standard exhibit formatting, legal/contractual tone, and examples from the company's existing templates
- Can be implemented as a simple chat-style input within the scope editor

**Template structure** (what a template looks like in the system):

```
SCOPE OF WORK — [TRADE NAME]
Project: [Auto-filled]
Date: [Auto-filled]

SECTION 1: GENERAL CONDITIONS (boilerplate, toggleable)
  □ Comply with all applicable codes and regulations
  □ Provide all labor, materials, equipment...
  □ Coordinate with other trades as required
  □ BIM coordination per project BIM Execution Plan    ← toggleable
  □ LEED documentation requirements                     ← toggleable
  □ Schedule of Values breakdown within 10 days...
  □ [12-20 more standard items]

SECTION 2: SCOPE OF WORK (project-specific, editable)
  [Free text — quantities, areas, drawing/spec references]
  [This is where PM describes what the sub is actually building]

SECTION 3: SPECIFIC INCLUSIONS (mix of boilerplate + custom)
  □ All permits and inspections for this trade          ← boilerplate
  □ [Custom items added per project]

SECTION 4: SPECIFIC EXCLUSIONS (mix of boilerplate + custom)
  □ Fire stopping of own penetrations (by others)       ← boilerplate
  □ [Custom items added per project]

SECTION 5: CLARIFICATIONS & ASSUMPTIONS
  [Project-specific — owner/architect conversations, design intent notes]
```

**Key design decisions**:
- Templates are structured as **blocks**, not free-form Word docs. Each boilerplate item is a toggleable unit. This enables: (a) quick customization, (b) future AI comparison against specs, (c) consistent output format.
- The system must track which boilerplate items were included/excluded per project — this becomes valuable data over time ("we always include BIM on lab projects but never on office TIs").
- Output is **PDF** (.pdf) — primary export for sharing, attaching to bids, and uploading to platforms (Procore, BuildingConnected). Teams use Bluebeam for markups/review. All editing happens inside the app, so Word export is not a priority.

**User Stories**:
- *As a PM, I want to see templates ranked by how similar the source project is to my current project so I pick the best starting point.*
- *As a PM, I want to toggle boilerplate items on/off rather than manually deleting paragraphs in Word so customization is faster and nothing gets accidentally left in.*
- *As a PE, I want to draft a scope exhibit and have my PM review it in the same tool so we're not emailing Word docs back and forth.*
- *As a PM, I want the tool to remember which boilerplate items I typically include for each project type so future projects auto-suggest the right defaults.*
- *As a PM, I want to describe my project and trade scope in plain English and have the AI generate exhibit-ready language so I don't have to write formal scope language from scratch.*
- *As a PM, I want to type a scope item in natural language and have the AI convert it to a standardized inclusion or exclusion block so the exhibit language is consistent and professional.*

---

### Workflow 3: Notes & Comments Tracker

**Who**: PM, PE, Superintendent (anyone on the project team)

**Current process**: Notes live nowhere. A Superintendent mentions in a meeting that caulking should be in the glazing scope. The PM has to remember this and manually make sure it shows up in the right scope exhibit. Notes from OAC meetings, field walks, and team conversations are lost unless someone happens to write them down and the right person sees them.

**New workflow**:

1. Any team member can add a **note** at any time — from the project dashboard, from within a specific trade's scope, or from a dedicated "Add Note" quick-entry
2. Each note has:
   - **Text**: The actual note (free text, concise)
   - **Primary trade**: Which trade this note primarily affects (required)
   - **Related trades**: Other trades that should be aware (optional, multi-select)
   - **Type** (select one):
     - **Scope clarification**: "Caulking is in glazing scope, not waterproofing"
     - **Open question**: "Who is carrying the dumpsters — each sub or GC central?"
     - **Means & methods**: "Superintendent wants HVAC rigging done on weekends"
     - **Owner/architect direction**: "Architect confirmed VCT in corridors, not LVT"
   - **Source**: Where this came from (meeting, field walk, email, phone call — optional, free text)
   - **Status**: Open / Resolved
   - **Resolution**: How it was resolved (free text, filled when closing)
3. Notes tagged to a trade appear in that trade's scope editor as a **sidebar panel** — the PM sees them while writing scope and can incorporate them into the exhibit
4. Notes tagged as "Open question" are highlighted differently — these are things that need a decision before the scope can be finalized
5. When an open question is resolved, the PM records the resolution and can optionally add the outcome as a new inclusion/exclusion item in the scope
6. **Cross-trade visibility**: If a note is tagged to multiple trades (e.g., "dumpsters" affects Demo, Drywall, Mechanical), it appears in all those trades' scope views. Resolving it in one place resolves it everywhere, but each trade's PM/PE can see the resolution.

**Example notes in practice**:

| Note | Primary Trade | Related Trades | Type | Status |
|------|--------------|----------------|------|--------|
| "Caulking at curtain wall is in glazing scope, not waterproofing" | 084000-Glazing | 071000-Waterproofing | Scope clarification | Open |
| "Who carries dumpsters and offhaul — each sub or central GC cost?" | 024100-Demo | 092900-Drywall, 230000-HVAC, 260000-Electrical | Open question | Open |
| "Super wants all rigging done on weekends — add to MEP scopes" | 230000-HVAC | 260000-Electrical, 210000-Fire Sprinkler | Means & methods | Open |
| "Architect confirmed: resilient flooring is LVT, not VCT. Spec is being revised." | 096500-Flooring | — | Owner/architect direction | Resolved |

**User Stories**:
- *As a PM, I want to quickly capture a scope-related note from a conversation so it doesn't get lost.*
- *As a PM, I want to see all open notes for a trade while I'm writing the scope exhibit so I can incorporate them.*
- *As a PE, I want to add notes from Superintendent conversations and tag them to the right trade(s) so the PM sees them when building scope.*
- *As a PM, I want to see all open questions across the entire project so I can systematically resolve them before issuing bids.*
- *As a PM, I want cross-trade notes to be visible in every affected trade so nothing falls through the cracks between scopes.*

---

### Workflow 4: Final Review (TurboTax-Style Checklist)

**Who**: PM (before issuing subcontract)

**Current process**: Gut feel. PM reviews the scope exhibit one last time, maybe asks a PE to double-check, and issues the subcontract. The most common failure: missed scope — something that wasn't clarified, the sub excluded it, and the GC assumed it was included. This results in change orders, disputes, and wasted time.

**New workflow**:

1. When the PM marks a trade as "Ready for Subcontract," the tool runs a **completeness check** and presents results as a step-by-step review:

   **Step 1: Open Notes Check**
   - Are there any unresolved notes for this trade?
   - Are there any open questions that haven't been answered?
   - ⚠️ **Blocks finalization** if open questions remain (can be overridden with justification)

   **Step 2: Cross-Trade Notes Check**
   - Are there notes tagged to this trade from other trades?
   - Have all cross-trade scope assignments been confirmed?
   - Example: "Note from Demo scope says 'each sub carries own dumpsters' — confirm HVAC scope includes dumpster language"

   **Step 3: Boilerplate Completeness**
   - Were any standard boilerplate items removed? Flag them for confirmation.
   - Example: "You removed 'BIM coordination' from this scope. Confirm this trade doesn't require BIM on this project."

   **Step 4: Bid Clarification Incorporation** *(V2 — when bid recap is added)*
   - Were all sub's exclusions/clarifications from their bid addressed in the subcontract exhibit?
   - Flag any sub exclusions that conflict with the scope exhibit

   **Step 5: Custom Checklist Items** *(per trade)*
   - Trade-specific checks that PMs add over time as lessons learned
   - Example for HVAC: "Did you confirm who provides the controls interface with BMS?"
   - Example for Electrical: "Did you clarify temporary power responsibilities?"
   - These grow organically as the team uses the tool — every "oh crap" moment becomes a future checklist item

2. The tool presents a **summary scorecard**:
   - ✅ All notes resolved
   - ✅ No cross-trade conflicts
   - ⚠️ 1 boilerplate item removed (confirmed by PM)
   - ❌ 2 open questions unresolved — **cannot finalize**

3. PM addresses any flags, then confirms. The scope exhibit is marked as "Finalized" and exported as final PDF.

4. **Lessons learned feedback loop**: After a project (or during), if a scope gap is discovered that wasn't caught, the PM can add it as a new checklist item for that trade. Next project, it's automatically part of the review.

**User Stories**:
- *As a PM, I want the system to warn me if I'm about to issue a subcontract with unresolved notes so I don't miss scope.*
- *As a PM, I want to see a clear pass/fail checklist before finalizing so I have confidence the scope is complete.*
- *As a PM, I want to add custom checklist items from lessons learned so the same mistake never happens twice.*
- *As a PM, I want the system to flag when I removed a standard boilerplate item so I confirm it was intentional and not an oversight.*
- *As a PM, I want cross-trade notes surfaced during final review so scope gaps between trades are caught before the subcontract is signed.*

---

### Workflow 5: Multi-User Collaboration

**Who**: PM + PE (typical project team)

**Current process**: PM tells PE what to do verbally or via email. PE drafts in Word, emails it back. PM edits, sends back. Multiple versions float around.

**New workflow**:

1. PM and PE both have access to the project in the tool
2. **Roles**:
   - **PM**: Full access. Can create projects, select templates, finalize scopes, manage templates
   - **PE**: Can draft/edit scope exhibits, add notes, but cannot finalize or export final subcontract exhibit without PM approval
3. PE drafts scope exhibits. PM reviews in the same tool — no emailing Word docs
4. Simple status tracking shows who last edited and when
5. Notes added by PE are visible to PM in real-time

**User Stories**:
- *As a PM, I want to assign a PE to draft a scope exhibit and review their work in the tool so we stop emailing Word docs.*
- *As a PE, I want to draft scope and add notes knowing the PM will see everything in context when they review.*

---

### Workflow 6: Template Library Management

**Who**: PM or company admin

**Current process**: No formal template management. Each PM maintains their own evolved versions of scope templates in personal folders or shared drives. Knowledge is siloed.

**New workflow**:

1. **Company master templates**: Maintained centrally. One per trade (by CSI code). Contains all possible boilerplate items for that trade — the "superset."
2. **Project templates**: When a PM creates a scope exhibit for a project, the final version is saved back as a project-specific instance. Future users can browse these as starting points.
3. **Template improvement flow**:
   - PM finishes a project and learned something (e.g., "always include controls interface clause for HVAC on lab projects")
   - PM can **propose** an addition to the company master template
   - Addition is tagged with project type relevance (e.g., "Lab TI only" or "All project types")
   - Over time, master templates get better because they absorb lessons learned from real projects
4. **Priority trades for initial templates**: Mechanical (HVAC), Electrical, Plumbing, Fire Sprinkler, Drywall, Doors. These are the big-ticket, high-complexity trades where scope exhibits matter most. Other trades can be added over time.

**User Stories**:
- *As a PM, I want a central library of company-approved templates so I'm not hunting through shared drives.*
- *As a PM, I want to contribute lessons learned back to the master template so the next PM benefits from my experience.*
- *As a company, we want templates to improve over time as more projects use the system so institutional knowledge compounds.*

---

### MVP Workflow Summary

The MVP delivers a **complete loop** with AI assistance:

```
PM creates project → Imports trade list → Selects template per trade
    → Describes project/scope in natural language → AI generates exhibit language
    → PM toggles boilerplate / edits project-specific scope
    → PM adds inclusions/exclusions via natural language → AI converts to exhibit language
    → Team adds notes (scope clarifications, open questions)
    → PM sees notes while editing scope → Incorporates them
    → Final review checklist catches gaps and unresolved items
    → Export PDF → Issue subcontract
```

**What's IN the MVP**:
- Template library & selection (by trade + project type)
- Scope editor with toggleable boilerplate blocks
- **AI scope language assistant** (project description → exhibit language, natural language → inclusions/exclusions)
- Notes & comments tracker (cross-trade, typed, status-tracked)
- Final review checklist (open notes, boilerplate check, custom items)
- Multi-user collaboration (PM/PE roles)
- PDF export

**What's NOT in MVP** (deferred to later phases):
- AI spec reading from uploaded PDFs (Stage 2)
- Cross-trade AI gap/overlap detection (Stage 4)
- Bid recap framework (Stage 5)
- Subcontract language conversion (Stage 6)

The MVP is valuable on its own: centralized templates + AI-assisted scope writing + captured notes + systematic review = fewer missed scope items and significantly faster exhibit creation.

---

## Technical Architecture / System Design

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      BROWSER (HTMX)                     │
│                                                         │
│  Buyout Dashboard │ Scope Editor │ Notes Panel │ Review │
└──────────┬──────────────────────────────────────────────┘
           │  HTML fragments (HTMX) + JSON (AI responses)
           │
┌──────────▼──────────────────────────────────────────────┐
│                    DJANGO APPLICATION                    │
│                                                         │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Projects│  │ Exhibits │  │  Notes   │  │ Reviews  │ │
│  │  Views  │  │  Views   │  │  Views   │  │  Views   │ │
│  └────┬────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
│       │            │            │              │        │
│  ┌────▼────────────▼────────────▼──────────────▼─────┐ │
│  │                  DJANGO ORM                        │ │
│  └────────────────────┬──────────────────────────────┘ │
│                       │                                 │
│  ┌────────────────────┼──────────────────────────────┐ │
│  │              AI SERVICE LAYER                      │ │
│  │  ┌──────────────┐  ┌───────────────────────────┐  │ │
│  │  │ Scope Writer │  │ Inclusion/Exclusion Gen.  │  │ │
│  │  │  (Claude API) │  │      (Claude API)         │  │ │
│  │  └──────────────┘  └───────────────────────────┘  │ │
│  └───────────────────────────────────────────────────┘ │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │              PDF EXPORT SERVICE                    │ │
│  │         (WeasyPrint or ReportLab)                 │ │
│  └───────────────────────────────────────────────────┘ │
└──────────┬──────────────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────────┐
│                    POSTGRESQL                            │
│                                                         │
│  Projects │ Trades │ CSITrades │ ScopeExhibits │         │
│  ExhibitSections │ ScopeItems │ Notes │ ChecklistItems │
└─────────────────────────────────────────────────────────┘
```

**Architecture style**: Standard Django monolith. No microservices, no separate frontend app. HTMX handles dynamic UI (toggling boilerplate, adding notes, AI responses) without a JavaScript framework. This is the simplest architecture that supports all MVP features.

**UI interaction approach**: The scope editor uses HTMX for all server interactions (toggles, form submissions, AI requests). For MVP, item reordering uses simple up/down arrow buttons (each button triggers an `hx-post` that swaps the item's `order` with its neighbor and returns the updated list). Post-MVP, **Sortable.js** (~2KB library) can be added alongside HTMX for drag-and-drop reordering — same backend logic, richer interaction. No JavaScript framework is needed for either approach.

### Data Models

#### Core Models

```
Company
├── id
├── name
└── created_at

User (extends Django auth)
├── company (FK → Company)
├── role: PM | PE | SUPERINTENDENT | ADMIN
└── [standard Django auth fields]

ProjectType (lookup table, admin-managed)
├── id
├── name: "Office TI" | "Lab TI" | "Core & Shell" | "Seismic Retrofit" | "Mixed-Use" | "Other"
└── description

CSITrade (lookup table, admin-managed)
├── id
├── csi_code: "231000"
├── name: "HVAC"
└── description (nullable)
```

#### Project & Trade Models

```
Project
├── id
├── company (FK → Company)
├── name: "456 Montgomery St - Lab TI"
├── number: "2026-0142"
├── project_type (FK → ProjectType)
├── description: text (nullable) — general project description (e.g., "5-story lab TI in existing office building, 45,000 SF, LEED Gold target")
├── address
├── created_by (FK → User)
├── created_at
└── updated_at

Trade
├── id
├── project (FK → Project)
├── csi_trade (FK → CSITrade) — links to trade code + name lookup
├── budget: Decimal
├── status: NOT_STARTED | SCOPE_IN_PROGRESS | OUT_TO_BID | BIDS_RECEIVED | SUBCONTRACT_ISSUED
├── assigned_to (FK → User, nullable) — PE assigned to draft
├── order: int — display order on dashboard
└── updated_at
```

#### Scope Exhibit Models

A ScopeExhibit is the central document — equivalent to the Word document today. Every exhibit has a `csi_trade` (what trade it's for) and optionally a `project` (which project context it belongs to). `is_template` is the source-of-truth for template intent. Templates can be global (`project=null`) or attached to company-managed "dummy projects" used as template buckets (e.g., by project type). Past project exhibits are also valid starting points for cloning.

```
ScopeExhibit
├── id
├── company (FK → Company)
├── csi_trade (FK → CSITrade) — always present; identifies the trade type (e.g., HVAC, Electrical)
├── project (FK → Project, nullable) — optional context; may be null for global templates
├── is_template: boolean (NOT NULL, default false) — source-of-truth template flag
├── scope_description: text (nullable) — natural language description of scope for AI context
├── status: DRAFT | READY_FOR_REVIEW | READY_FOR_BID | FINALIZED
├── based_on (FK → ScopeExhibit, nullable) — which template/past exhibit this was cloned from
├── last_edited_by (FK → User)
├── created_by (FK → User)
├── created_at
└── updated_at

ExhibitSection
├── id
├── scope_exhibit (FK → ScopeExhibit)
├── name: "General Scope of Work" | "Specific Scope of Work" | "Alternates & Exclusions" | [custom]
├── order: int — display/document order
├── created_at
└── updated_at

ScopeItem
├── id
├── section (FK → ExhibitSection) — which section this item belongs to
├── parent (FK → ScopeItem, nullable) — null = top-level item
├── level: int (default 0) — nesting depth (0 = top-level, 1 = sub-item, 2 = sub-sub-item)
├── text: text — the exhibit language
├── original_input: text (nullable) — what PM typed if AI-generated
├── is_ai_generated: boolean
├── order: int — display order within siblings at same level
├── created_by (FK → User)
├── created_at
└── updated_at
```

**Creating from a template or past exhibit**: PM selects a starting point (either a template or a finalized past exhibit). The system clones the entire ScopeExhibit — copies the ExhibitSections and all ScopeItems into a new exhibit linked to the project. Sets `based_on` to the source. From that point, it's a fully independent document.

**Saving as template**: PM finishes a project exhibit and wants to save it as a reusable template. The system clones it into a new ScopeExhibit with `is_template=true`. PM can keep `project=null` (global template) or attach it to a company-managed dummy project (project-type template bucket).

**Template selection UI**: "Pick a starting point" shows both templates (`is_template=true`, filtered by `csi_trade`) and past project exhibits (`is_template=false`, `status=FINALIZED`, same `csi_trade`, sorted by project type similarity). No distinction needed in the picker — they're all starting points.

**Trade linkage decision (MVP)**: Keep `csi_trade` on ScopeExhibit and do not add a direct `trade` FK yet. To preserve integrity, enforce one Trade per `(project, csi_trade)` and join exhibits to workflow state through that pair. This keeps the schema simpler while supporting the current buyout lifecycle.

#### Notes Models

```
Note
├── id
├── project (FK → Project)
├── primary_trade (FK → Trade)
├── related_trades (M2M → Trade)
├── text: text
├── note_type: SCOPE_CLARIFICATION | OPEN_QUESTION | MEANS_METHODS | OWNER_ARCHITECT_DIRECTION
├── source: text (nullable) — "OAC meeting 2/15", "field walk", etc.
├── status: OPEN | RESOLVED
├── resolution: text (nullable)
├── resolved_by (FK → User, nullable)
├── resolved_at: datetime (nullable)
├── created_by (FK → User)
├── created_at
└── updated_at
```

#### Review / Checklist Models

**MVP approach**: The review system is **informational, not blocking**. Running a Final Review generates a checklist of items to review, but does not prevent the PM from exporting or issuing the exhibit. Think of it as a "health check" — the PM sees warnings and can optionally respond, but can move forward regardless. ChecklistItems are admin-seeded via Django admin only (no user-facing creation UI in MVP).

```
ChecklistItem (trade-level lessons learned, admin-seeded via Django admin)
├── id
├── company (FK → Company)
├── csi_trade (FK → CSITrade) — which trade this applies to
├── text: "Confirm who provides controls interface with BMS"
├── project_type_tags (M2M → ProjectType) — optional, can be scoped to project types
├── created_by (FK → User)
├── source_project (FK → Project, nullable) — which project created this lesson (null = general best practice)
└── created_at

FinalReview (one per ScopeExhibit — re-running replaces the previous review)
├── id
├── scope_exhibit (FK → ScopeExhibit)
├── initiated_by (FK → User)
├── initiated_at: datetime
├── completed_at: datetime (nullable)
└── status: IN_PROGRESS | COMPLETED

FinalReviewItem (individual check results)
├── id
├── final_review (FK → FinalReview)
├── check_type: OPEN_NOTE | CROSS_TRADE | CUSTOM_CHECKLIST
├── description: text — what was flagged
├── status: PASS | WARNING | FAIL — informational severity (does not block issuing)
├── pm_response: text (nullable) — optional PM notes/confirmation
└── reviewed_at: datetime (nullable)
```

### Key Relationships & Queries

The data model supports these critical views:

| View | Query Pattern |
|------|--------------|
| Buyout dashboard | All Trades for a Project, grouped by status |
| Template / starting point selection | ScopeExhibits where (`is_template=true` OR (`is_template=false` AND `status=FINALIZED`)) AND `csi_trade` matches. Sorted: company master templates first, then past exhibits with exact project type match, then remaining past exhibits by date (most recent first). |
| Scope editor | ScopeExhibit → ExhibitSections (ordered) → ScopeItems per section (ordered, hierarchical) |
| Notes sidebar | Notes where primary_trade = this trade OR this trade in related_trades |
| Project-wide open questions | Notes where project = this project AND note_type = OPEN_QUESTION AND status = OPEN |
| Final review | Automated queries against Notes, ChecklistItems for the trade |

### AI Service Layer

The AI integration is isolated in a service module (`services/ai.py`) with two functions:

```python
# Function 1: Scope description → exhibit language
def generate_scope_from_description(
    trade_name: str,           # from csi_trade.name
    csi_code: str,             # from csi_trade.csi_code
    project_type: str,         # from project.project_type.name
    project_description: str,  # from project.description
    scope_description: str,    # from scope_exhibit.scope_description
    existing_sections: list[dict],  # current sections and their items for context
) -> dict:
    """
    Returns:
    {
        "scope_items": [              # Suggested ScopeItems organized by section
            {
                "section_name": "General Scope of Work",
                "items": [
                    {"text": "...", "level": 0},
                    {"text": "...", "level": 1},
                ]
            },
            ...
        ],
    }
    """

# Function 2: Natural language → scope item
def generate_scope_item(
    input_text: str,
    trade_name: str,
    section_name: str,               # which section the item is being added to
    existing_scope_context: str,      # current exhibit content for context
) -> dict:
    """
    Returns:
    {
        "exhibit_text": "...",        # Standardized exhibit language
    }
    """
```

**System prompt strategy**: Each function uses a system prompt that includes:
- Trade-specific terminology and conventions
- Standard exhibit formatting rules (capitalize trade names, reference drawings as "per Drawing X.X", use "provide and install" not "supply")
- Legal/contractual tone guidelines
- Examples from the company's existing templates (seeded initially, grows over time)
- The current exhibit context (what's already in the scope) to avoid duplication

**API choice**: Claude API (Sonnet for speed/cost — these are structured text generation tasks, not complex reasoning). Falls back gracefully if API is unavailable — PM can always type exhibit language manually.

### PDF Export

The export pipeline converts the structured scope data into a formatted PDF:

```
ScopeExhibit data → Django template (HTML) → PDF renderer
```

- **HTML template** defines the exhibit layout (header, sections, page breaks, formatting)
- **WeasyPrint** (or ReportLab) converts HTML → PDF
- Company logo (static placeholder image for MVP; post-MVP: add `logo` ImageField to Company model for per-company branding), project info, and date auto-populated in header
- ExhibitSections rendered in their defined order, each with its ScopeItems in hierarchical numbering
- Clean, professional output matching industry-standard exhibit formatting

### Component Architecture (Django Apps)

```
scope_manager/                  # Django project
├── core/                       # Shared: Company, User, ProjectType, CSITrade
├── projects/                   # Project, Trade, buyout dashboard
├── exhibits/                   # ScopeExhibit, ExhibitSection, ScopeItem, editor views
├── notes/                      # Note, notes panel views
├── reviews/                    # ChecklistItem, FinalReview, FinalReviewItem
├── ai_services/                # Claude API integration, prompt management
├── exports/                    # PDF generation
└── templates/                  # Django HTML templates (HTMX partials)
    ├── base.html
    ├── projects/
    ├── exhibits/
    ├── notes/
    └── reviews/
```

### HTMX Interaction Patterns

The UI is server-rendered HTML with HTMX for dynamic behavior — no JavaScript framework needed.

| Interaction | HTMX Pattern |
|------------|--------------|
| Add/rename/delete/reorder section | `hx-post`/`hx-patch`/`hx-delete` → updates ExhibitSection → returns re-rendered section list |
| Add/delete scope item | `hx-post`/`hx-delete` → creates or removes ScopeItem → returns re-rendered section |
| Reorder scope item (up/down) | `hx-post` → swaps `order` with neighbor item → returns re-rendered item list. **Subtree moves as a unit**: moving a parent item moves all its children with it. |
| Indent/outdent scope item | `hx-post` → updates `parent` and `level` → returns re-rendered item with updated numbering. **Cascades to children**: indenting/outdenting a parent shifts all descendants by the same amount. |
| Add note from sidebar | `hx-post` → creates Note → returns updated notes list partial |
| AI: generate scope from description | `hx-post` → calls Claude API → returns generated items directly inserted into relevant exhibit sections (with loading indicator). PM edits in place after insertion. |
| AI: generate inclusion/exclusion | `hx-post` → calls Claude API → returns preview partial for accept/edit/reject |
| Change trade status | `hx-patch` → updates Trade.status → returns updated dashboard row |
| Final review initiation | `hx-post` → runs checks → returns review checklist partial |
| Resolve note | `hx-patch` → updates Note status/resolution → returns updated note card |

**Loading states**: AI calls take 2-5 seconds. Use `hx-indicator` to show a spinner while waiting for Claude API response. The rest of the app (toggles, notes, status changes) is near-instant.

**Item editing (MVP)**: Each scope item renders as an inline editable field. Clicking on an item switches it to edit mode (a `<textarea>` that auto-sizes). On blur or Enter, `hx-patch` saves the updated text and returns the rendered item. Items display with **hierarchical numbering** (1, 1.1, 1.1.1, etc.) computed server-side from the `parent`/`level`/`order` fields. Indent/outdent controls (Tab/Shift+Tab or buttons) let users nest items, and up/down arrow buttons handle reordering. Both the scope editor and the PDF export render the full hierarchical numbering.

**Subtree behavior**: Items with children always move as a group. Reordering a parent item (up/down) carries its entire subtree with it — the children maintain their relative structure and simply move with the parent. Indenting/outdenting a parent cascades to all descendants (e.g., indenting a level-0 item makes it level-1, and its level-1 children become level-2). The server handles this by querying all descendants of the affected item and updating their `parent`/`level` fields in a single operation.

### Post-MVP Architecture Notes

The following features are **not in MVP** but the architecture is designed to support them without structural changes:

**1. Drag-and-Drop Reordering**
- MVP uses up/down arrow buttons for item reordering (pure HTMX, no JS libraries)
- Post-MVP: add **Sortable.js** (~2KB) alongside HTMX for drag-and-drop interaction
- Same backend endpoint — Sortable.js fires an event on drop that triggers the existing `hx-post` reorder endpoint with the new position
- No architecture changes needed; the `order` field on ScopeItem already supports this

**2. Track Changes**
- Post-MVP feature for PM review of PE edits (similar to Word's track changes)
- Implementation approach: **django-simple-history** or a custom `ScopeItemHistory` model that logs every edit:
  ```
  ScopeItemHistory
  ├── id
  ├── scope_item (FK → ScopeItem)
  ├── previous_text: text
  ├── new_text: text
  ├── changed_by (FK → User)
  ├── changed_at: datetime
  └── action: CREATED | EDITED | DELETED | REORDERED | INDENT_CHANGED
  ```
- A "Review Changes" view renders diffs (old vs. new, highlighted) for the PM
- PM can accept or reject each change, which either keeps or reverts the edit
- No WebSockets or real-time sync needed — standard request-response pattern
- The existing `last_edited_by` field on ScopeExhibit already tracks who last touched the document; the history model adds granular per-item tracking

~~**3. Hierarchical Numbering Display** — Moved to MVP (see HTMX Interaction Patterns above)~~

**4. AI-Powered Boilerplate Toggle Suggestions & Template/Item Recommendations**
- MVP: PM manually selects a template/past exhibit as starting point, and manually adds/edits items with AI language assistance. Boilerplate items are toggled manually.
- Post-MVP: the AI uses the `scope_description` field (and `project.description` for broader context) to:
  - **Suggest boilerplate toggles**: based on the scope description, auto-suggest which boilerplate items to enable/disable (e.g., auto-enables "BMS integration" and "lab exhaust" for a lab project, disables "new AHU installation")
  - **Recommend starting points**: rank templates and past exhibits by relevance to the current scope description (semantic similarity, not tags)
  - **Suggest scope items**: based on the scope description, suggest new items or modifications to existing items within the exhibit (e.g., "This is a lab project — consider adding fume hood exhaust connections to your HVAC scope")
  - **Flag missing scope**: compare scope description against the current exhibit and surface gaps (e.g., "You mentioned BMS integration but no scope item addresses controls coordination")
- Implementation: additional Claude API calls that take the scope description + project description + current exhibit state and return suggestions. Displayed as a sidebar or inline suggestions the PM can accept/dismiss.
- No data model changes needed — suggestions are transient (generated on demand, not stored)

**5. Project Membership & Invitations**
- MVP: all users in a company can see all projects (no access restrictions)
- Post-MVP: add a `ProjectMember` through-table linking Users to Projects with a role (e.g., PM, PE, view-only)
  ```
  ProjectMember
  ├── id
  ├── project (FK → Project)
  ├── user (FK → User)
  ├── role: PM | PE | VIEW_ONLY
  └── added_at: datetime
  ```
- Project and company admins can invite users to specific projects
- Users only see projects they're members of (filtered in views via `ProjectMember` queryset)
- Existing data migration: when enabled, auto-create ProjectMember records for all users in the company for all existing projects

**6. Blocking Review Workflow**
- MVP: Final Review is informational — PM sees warnings but nothing is blocked from being issued
- Post-MVP: Final Review becomes a gate. Changes:
  - FinalReview status expands: `IN_PROGRESS | COMPLETED | PASSED | PASSED_WITH_OVERRIDES | BLOCKED`
  - Add `is_override: boolean` to FinalReviewItem — distinguishes "PM confirmed this is addressed" (PASS) from "PM acknowledged but is overriding" (override with justification in `pm_response`)
  - PM must resolve or override all FAIL items before exhibit can move to `READY_FOR_BID`
  - Overall status derived: all PASS → `PASSED`, any overrides → `PASSED_WITH_OVERRIDES`, unresolved FAILs → `BLOCKED`

**7. User-Submitted ChecklistItems with Approval Workflow**
- MVP: ChecklistItems are admin-seeded only (via Django admin). No user-facing creation UI.
- Post-MVP: PM/PE can submit new ChecklistItems from the app UI. Add `status: PENDING | APPROVED` field to ChecklistItem. New items created with `status = PENDING`. Admin reviews and approves via Django admin (or a simple approval view). During Final Review, only `APPROVED` items are pulled. No structural model changes — just one field, a queryset filter, and the submission UI.

**8. Additional Model Fields (Deferred)**
- `Trade.spec_section`: text (nullable) — reference to the relevant spec section number (e.g., "23 21 13"). Useful when AI spec reading is added in V2 to link trades to their spec sections.
- `Trade.bid_due_date`: date (nullable) — when bids are due for this trade. Enables dashboard sorting/filtering by urgency. Currently tracked in BuildingConnected, so this would be a convenience duplicate.
- `Project.status`: ACTIVE | COMPLETED | ARCHIVED — allows archiving old projects so they don't clutter the dashboard. Archived projects remain searchable for template reuse but don't appear in the active project list.

---

## Tech Stack & Rationale

| Technology | Purpose | Why This Choice |
|-----------|---------|-----------------|
| **Django 5.x** | Web framework | Owner's strongest skill. Proven track record shipping Django apps. ORM handles the relational data model well. Built-in auth, admin, forms. |
| **PostgreSQL** | Database | Production-grade relational DB. Handles the structured data model (projects → trades → scopes → items). Free tier on Railway/Render. Django's best-supported DB. |
| **HTMX** | Dynamic UI | No JavaScript framework needed. Server-rendered HTML with dynamic behavior (toggles, notes, AI responses). Owner has HTMX experience from Real Estate Calculator project. |
| **Claude API (Sonnet)** | AI scope generation | Structured text generation tasks — Sonnet is fast and cost-effective for this. Owner has Claude Pro subscription. Strong at following formatting instructions and maintaining professional tone. |
| **WeasyPrint** | PDF export | Python library that converts HTML/CSS → PDF. Lets us use Django templates for exhibit layout — same skill set, no new tooling. Good typography and page control. |
| **Tailwind CSS** | Styling | Utility-first CSS. Fast to build professional UI without writing custom CSS. Good component patterns for dashboards, forms, editors. |
| **django-allauth** | Authentication | Handles login/logout/change-password pages. **Self-registration disabled for MVP** — admin creates user accounts via Django admin (email, name, company, role, password). No email infrastructure needed. Post-MVP: add invite flow (admin enters email → system sends invite link → user sets own password via SendGrid or similar). |
| **Railway or Render** | Hosting | Simple deployment from Git. Free/cheap tiers for MVP. PostgreSQL included. No DevOps overhead. |

### Alternatives Considered

| Alternative | Why Not |
|------------|---------|
| **React/Next.js frontend** | Adds complexity (separate frontend app, API layer, deployment). HTMX achieves the needed interactivity without a JS framework. Owner's JS skills are beginner-level. |
| **GPT-4 / OpenAI API** | Claude Sonnet is comparable for this task and owner already has Claude Pro. Could swap later if needed — AI service layer is abstracted. |
| **python-docx (Word export)** | Initially considered for Word output, but since editing happens in-app, PDF is the primary export. Eliminates dependency. Can add Word export later if users request it. |
| **ReportLab (PDF)** | Lower-level than WeasyPrint. Would require more code to achieve the same layout. WeasyPrint lets us reuse HTML/CSS skills. |
| **SQLite** | Fine for local dev, but PostgreSQL is needed for multi-user production deployment. Start with PostgreSQL from day one to avoid migration pain. |

---

## Development Phases / Milestones

### Development Philosophy

The plan is structured around one principle: **close the core value loop as fast as possible**.

The minimum viable loop is:
```
Create project → Pick template → Edit exhibit → Export PDF
```

Everything else (notes, AI, final review) makes that loop better but isn't required. The goal is to reach a usable PDF output by **end of Week 5**, not Week 7, so you can start using the tool yourself immediately — even without notes, AI, or final review, this replaces the Word template workflow.

---

### Phase 1: Foundation + Data Models (Week 1)

**Rationale**: Merge project setup and data models into one task. There's no reason to separate "create the project skeleton" from "create the models" — they're one setup task. You won't ship anything between them.

**What's being built**:
- Django project structure + all 5 apps (`core`, `projects`, `exhibits`, `notes`, `reviews`)
- Settings configuration: PostgreSQL, django-allauth (email auth, no self-registration), HTMX, Tailwind CDN
- Custom User model (email-based, company FK, role field) + Company model
- **ALL data models** across all apps — get migrations done once
  - Core: `Company`, `User`, `ProjectType`, `CSITrade`
  - Projects: `Project`, `Trade`
  - Exhibits: `ScopeExhibit`, `ExhibitSection`, `ScopeItem`
  - Notes: `Note`
  - Reviews: `ChecklistItem`, `FinalReview`, `FinalReviewItem`
- Django admin configured for every model
- Seed data command (CSI trades, project types)
- Factory Boy factories for every model
- Company-scoping mixin + role helpers
- Base layout template (nav, flash messages, content block)
- Pytest config + CI script
- Model constraint tests

**Why all models upfront**: Django migrations are easier when you define your schema in one pass. Adding models later means dealing with migration dependencies across apps. The models are already fully designed in the architecture section — just implement them. The time cost is low and it prevents migration headaches later.

**Exit criteria**: Auth works, all models migrated, admin can seed data, CI passes, factories create valid test data.

---

### Phase 2: Project Dashboard + Trade Setup (Week 2)

**Rationale**: This is the entry point to the app — the first thing users see after login. Get the foundation of project management working before diving into the complex scope editor.

**What's being built**:
- Project list view (company-scoped)
- Project create/edit forms
- Trade import: paste-based parser (CSI code + name + budget, one per line)
- Manual single-trade add (CSI dropdown + budget)
- Buyout dashboard: trades table grouped by status, stats bar
- Trade status update via HTMX (dropdown → instant update)
- Trade PE assignment via HTMX
- Integration tests: company isolation, import parser edge cases

**Key service**: `parse_trade_import()` — this needs to be robust. Handle tabs, commas, dollar signs, spaces in CSI codes, blank lines, duplicates. Write 8-10 test cases for this function alone.

**Exit criteria**: PM can create a project, paste 15+ trades from a spreadsheet, see a clean dashboard, update statuses — all without full page reloads.

---

### Phase 3: Scope Exhibit Editor (Weeks 3-4)

**Rationale**: This is the core product and the most complex phase. **~40% of total development time**. The clone service's parent FK remapping and the indent/outdent cascade logic are the two hardest algorithms in the app. They need careful implementation and testing. Rushing this phase creates ordering bugs that corrupt exhibits.

#### Week 3 — Template picker + clone + basic editor

**What's being built**:
- Template/past exhibit picker (filtered by CSI trade, sorted by project type match)
- Clone service (deep copy with parent FK remapping — the trickiest piece of code in the app)
- Create-blank-exhibit service (5 default sections)
- Editor page layout: two-column (content left, sidebar right)
- Section CRUD: add, rename, delete, reorder (HTMX)
- Item CRUD: add (opens in edit mode), click-to-edit, delete (with descendants)

#### Week 4 — Hierarchy + polish

**What's being built**:
- Item reordering: up/down with subtree integrity
- Item indent/outdent with cascade to descendants
- Hierarchical numbering (server-side computation: 1, 1.1, 1.1.1)
- Scope description textarea (saved to DB — used by AI later)
- Save-as-template flow
- Exhibit status transitions (DRAFT → READY_FOR_REVIEW → READY_FOR_BID → FINALIZED) with Trade status sync
- Thorough editor integration tests

**Exit criteria**: Full editor workflow — pick template → clone → edit sections/items → reorder → indent/outdent → save. Hierarchical numbering correct after every operation. Status transitions work.

---

### Phase 4: PDF Export (Week 5, first half)

**Rationale**: **This is where the plan diverges from typical approaches.** PDF export is moved here (instead of bundling it late with Final Review) because:
1. **It's simple** — HTML template + WeasyPrint is 6-8 hours of work
2. **It closes the value loop** — after this phase, you have a genuinely usable tool that replaces the Word template workflow
3. **You can start using it yourself immediately** — even without notes, AI, or final review
4. **It's motivating** — seeing a real, professional PDF come out of your app is a huge morale boost mid-build

**What's being built**:
- PDF HTML template: professional exhibit layout (header, sections, hierarchical items, page numbers, company name)
- Print CSS: `@page` rules, margins, typography
- WeasyPrint service: `generate_exhibit_pdf()` → returns bytes
- Download view: `Content-Disposition: attachment; filename="ExhibitA_HVAC_ProjectName.pdf"`
- "Export PDF" button in editor footer
- Test with varying exhibit sizes (1-page, 5-page, 10-page)

**Exit criteria**: Clicking "Export PDF" downloads a clean, professional Exhibit A document. Tested at multiple sizes. Hierarchical numbering matches the editor display.

---

### Phase 5: Notes & Cross-Trade Tracking (Week 5, second half + Week 6 first half)

**Rationale**: Now we start layering on features that make the core loop better. The basic app works — notes add collaboration and context capture.

**What's being built**:
- Note model already exists from Phase 1 — now build the UI
- Note creation form (primary trade + related trades + type + source)
- Notes sidebar embedded in scope editor (loads via HTMX)
- Cross-trade visibility: note tagged to HVAC + Electrical appears in both editors
- Note resolution flow (resolve with text, update status)
- Project-level open questions view (all unresolved questions across trades)
- Open questions badge on buyout dashboard
- Tests: cross-trade visibility, company isolation, resolution persistence

**Exit criteria**: Notes appear in all relevant trade contexts. Open question count accurate. Resolve action persists correctly. Dashboard shows open question count.

---

### Phase 6: AI Scope Assistant (Week 6, second half + Week 7 first half)

**Rationale**: This is the "wow factor" feature but it's intentionally late because **the app must work perfectly without it**. AI is additive, not foundational.

**What's being built**:
- AI service layer: `generate_scope_from_description()` and `generate_scope_item()`
- System prompts: exhibit language conventions, trade-specific context, JSON output schema
- Response parsing with fallback on malformed JSON
- Error handling: 30s timeout, 1 retry on 5xx, graceful failure message
- Feature flag: `AI_ENABLED` setting — everything works if AI is off
- `AIRequestLog` model for metrics (response time, tokens, success/failure — no prompt text stored)
- Editor integration #1: scope description textarea → "Generate Scope" button → items inserted into sections
- Editor integration #2: per-section natural language input → AI preview → accept/edit/reject
- Tests with mocked API (no real API calls in tests)

**Key design decision**: AI suggestions are inserted as regular `ScopeItems` with `is_ai_generated=True`. Once accepted, they're indistinguishable from manually created items. The PM edits them like anything else. No special "AI mode" — it's just a faster way to add items.

**Exit criteria**: Both AI functions work end-to-end. Failures degrade gracefully. PM can complete any exhibit with or without AI. Metrics logged.

---

### Phase 7: Final Review + Hardening + Launch (Weeks 7-8)

**Rationale**: Combine the review feature with hardening and launch prep. The review is a quality layer — important but not the core product.

#### Week 7: Final Review

**What's being built**:
- Review generation service: runs three checks (open notes, cross-trade notes, checklist items)
- Review UI: checklist display with summary scorecard, PM response fields
- "Run Final Review" button in editor
- Informational only (warnings, not blockers) — PM can proceed regardless
- Tests for review generation logic

#### Week 8: Hardening + Pilot Launch

**What's being built**:
- Sentry error tracking
- Query performance audit (N+1 queries, missing indexes)
- Security audit: every view checked for auth + company isolation + role enforcement
- Production deployment (Railway or Render): gunicorn, WhiteNoise, env vars, SSL
- Seed production data: company, users, real trade templates (from existing Word docs), checklist items

**Pilot launch**:
- 2-3 PMs + their PEs
- Brief onboarding guide (1-page, not a manual)
- Weekly check-ins for 2-3 weeks
- Track KPIs from Success Metrics section

**Exit criteria**: No P0/P1 bugs. Production stable. Pilot users completing full workflow. Security audit passed.

---

### Timeline Summary

| Phase | Duration | Cumulative Weeks | Core Deliverable |
|-------|----------|------------------|------------------|
| Phase 1: Foundation + Data Models | Week 1 | Week 1 | All models, auth, CI setup |
| Phase 2: Project Dashboard + Trade Setup | Week 2 | Week 2 | Project creation, trade import, dashboard |
| Phase 3: Scope Exhibit Editor | Weeks 3-4 | Week 4 | Full editor with hierarchy, reordering, templates |
| Phase 4: PDF Export | Week 5 (first half) | Week 5 | **Usable PDF output — core loop complete** |
| Phase 5: Notes & Cross-Trade Tracking | Week 5-6 (1.5 weeks) | Week 6 | Collaboration features |
| Phase 6: AI Scope Assistant | Week 6-7 (1.5 weeks) | Week 7 | AI-assisted scope generation |
| Phase 7: Final Review + Hardening + Launch | Weeks 7-8 | Week 8 | Production-ready, pilot launched |

**Total: 6-8 weeks** at ~20 hrs/week (114-160 hours total development time)

**Key milestone**: End of Phase 4 (Week 5) — you have a working tool that replaces the Word template workflow. Everything after that makes it better.


## Time & Cost Estimates

Estimates below assume:
- Solo builder at ~20 hrs/week.
- AI coding tools used for scaffolding/tests.
- MVP scope exactly as defined (paste-only import, lightweight Playwright, informational review, no invite flow).
- Pilot with a few selected users and low-to-moderate usage.

### Development Time Estimate (Hours)

| Phase | Hours (Aggressive) | Hours (Typical) | Notes |
|------|---------------------|-----------------|-------|
| Phase 0: Foundation | 10 | 14 | Project bootstrap, auth skeleton, CI |
| Phase 1: Data model + admin seeding | 14 | 20 | Models, migrations, admin, seed scripts |
| Phase 2: Project/trade setup + dashboard | 14 | 20 | Project create flow, paste import, dashboard HTMX |
| Phase 3: Scope editor + templates | 24 | 34 | Core complexity center (clone, hierarchy, ordering) |
| Phase 4: Notes + cross-trade visibility | 12 | 16 | Note model logic + scope sidebar |
| Phase 5: AI assistant integration | 16 | 22 | Service layer, parsing, retries/fallback |
| Phase 6: Final review + PDF export | 14 | 18 | Checklist generation + export templates |
| Phase 7: Hardening + pilot launch | 10 | 16 | Bug fixing, logging, perf/security pass |
| **Total** | **114 hrs** | **160 hrs** | |

### Schedule Translation (at 20 hrs/week)

- **Aggressive path**: ~114 hrs -> **about 6 weeks**.
- **Typical path**: ~160 hrs -> **about 8 weeks**.
- **Buffer recommendation**: reserve 10-15 additional hours for pilot feedback fixes.

### One-Time Build/Setup Costs (MVP)

| Item | Estimate |
|------|----------|
| Domain + DNS (optional if using platform subdomain for pilot) | $0-20 |
| UI template/components (optional) | $0-100 |
| Misc tooling/services during build | $0-50 |
| **Total one-time** | **$0-170** |

### Monthly Operating Cost Estimate

These ranges are intentionally conservative and should be validated at account setup time.

| Cost Bucket | Pilot (few users) | Early Production (10-25 users) | Notes |
|------------|--------------------|----------------------------------|-------|
| App hosting + PostgreSQL | $20-60/mo | $60-180/mo | Depends on provider tier, DB size, and uptime requirements |
| AI API usage (scope generation) | $15-75/mo | $75-350/mo | Driven by number/length of generation calls per trade |
| Error tracking/monitoring | $0-26/mo | $26-80/mo | Free tier usually enough for pilot |
| Email/transactional notifications (minimal MVP) | $0-15/mo | $15-40/mo | Mostly post-MVP if invite flows are added |
| File storage/backups/log retention | $0-20/mo | $20-60/mo | Varies by retention and export volume |
| **Estimated monthly total** | **$35-196/mo** | **$196-710/mo** | |

### Practical Budget Guidance

1. **Pilot target budget**: plan around **$75-200/month**.
2. **Early production budget**: plan around **$250-700/month** depending mostly on AI usage and hosting tier.
3. Control costs by:
   - Caching repeated template-derived AI prompts.
   - Using rate limits per user/project.
   - Keeping PDF rendering synchronous only for on-demand export (no background bulk jobs in MVP).

### Time/Cost Risk Multipliers

- If scope expands (CSV upload, drag-and-drop sorting, blocking review workflow), add **+20 to +45 hours**.
- If AI output quality requires multiple prompt iteration cycles, add **+8 to +20 hours**.
- If pilot users request major UX adjustments, add **+10 to +30 hours**.

---

## Risks & Challenges

This section prioritizes MVP risks by likelihood and impact, with concrete mitigation actions.

### Risk Register (MVP)

| # | Risk | Likelihood | Impact | Why It Matters | Mitigation | Contingency Trigger |
|---|------|------------|--------|----------------|------------|---------------------|
| 1 | **Scope creep during build** | High | High | Extra features (CSV upload, drag-drop, blocking review) can quickly break the 6-8 week target. | Enforce strict MVP boundary; keep a deferred backlog; no in-sprint feature additions unless replacing another item. | If weekly planned hours slip by >20%, freeze scope and cut non-critical polish immediately. |
| 2 | **Hierarchy/order bugs in scope editor** | Medium | High | Reordering and nesting logic (`parent` + `level` + `order`) is core complexity and can corrupt exhibits. | Centralize reorder logic in service layer; add strong unit tests for move up/down, reparenting, and edge cases. | If ordering defects recur after fixes, temporarily reduce to single-level ordering for pilot stability. |
| 3 | **AI output inconsistency/quality drift** | Medium | High | Poor exhibit language reduces trust and causes manual rework. | Use strict prompt templates, output schema validation, and fallback to manual edit flow. Add PM review before acceptance. | If acceptance rate falls below target, reduce AI usage to item-level generation only until prompts are tuned. |
| 4 | **Permissions/tenant isolation defects** | Medium | High | Cross-company data exposure is unacceptable and blocks pilot/production use. | Apply company filters in queryset/service layer by default; add integration tests for all major views and actions. | Any leakage bug is P0: pause rollout, patch immediately, and run full permission regression suite. |
| 5 | **Underestimated testing effort** | Medium | Medium-High | Fast delivery without tests creates fragile releases during pilot. | Timebox minimum test suite per phase: model/service unit tests + integration tests + Playwright smoke path. | If test backlog exceeds one week, stop new feature work until core test gates pass. |
| 6 | **PDF formatting instability across real exhibits** | Medium | Medium | Export quality is a key deliverable; malformed PDFs hurt adoption. | Create a print template baseline and approval snapshots for representative trade exhibits (short/long/complex). | If formatting breaks in pilot docs, provide “safe template” fallback format while patching CSS/layout. |
| 7 | **Pilot adoption friction (workflow change)** | Medium | Medium | PM/PE may revert to Word if app flow feels slower initially. | Start with a few selected users, provide short onboarding scripts, and collect feedback weekly. | If users abandon flow, prioritize top 2 friction points before adding new features. |
| 8 | **Operational blind spots in early production** | Low-Medium | Medium | Without logs/metrics, diagnosing failures (AI, DB, PDF) is slow. | Add baseline observability: error tracking, request latency, AI token/cost/error metrics. | If unresolved incidents repeat, expand instrumentation before scaling users. |

### Technical Challenges to Solve Early

1. **Deterministic ordering model**
   - Challenge: consistent behavior when moving items across levels/sections.
   - Approach: one reorder service with transactional updates and invariant checks.

2. **Template cloning correctness**
   - Challenge: clone large exhibits with hierarchy intact and correct lineage (`based_on`).
   - Approach: clone service with integration tests on multi-level sections/items.

3. **Cross-trade note visibility performance**
   - Challenge: note queries can become expensive as projects scale.
   - Approach: index key fields and optimize queryset patterns early.

4. **AI reliability without storing prompts/responses**
   - Challenge: debugging quality issues with privacy-constrained logging.
   - Approach: log token/cost/error + request type + latency + acceptance action metadata.

### Product/Execution Challenges

1. **Balancing speed vs confidence**
   - Pressure to move quickly can reduce test depth.
   - Mitigation: maintain non-negotiable release gates for core flows.

2. **Aligning pilot feedback with roadmap**
   - Pilot users may request many improvements at once.
   - Mitigation: classify feedback into P0/P1/P2 and apply weekly triage.

3. **Maintaining focused weekly progress**
   - With a 20 hrs/week cadence, context switching can stall momentum.
   - Mitigation: plan one primary phase objective per week and avoid parallel unfinished tracks.

### Risk Monitoring Cadence

- **Weekly (during build)**:
  - Planned vs actual hours
  - Open P0/P1 defect count
  - Test pass rate (unit/integration/smoke)
  - AI failure rate and manual fallback frequency
- **Pilot checkpoint (end of each week)**:
  - User completion rate for core workflow
  - Top 3 friction points
  - Decision: continue, stabilize, or trim scope

---

## Success Metrics / KPIs

KPIs are organized by phase so decisions are data-driven from MVP build through pilot.

### KPI Framework

1. **Delivery KPIs**: Are we building predictably and safely?
2. **Workflow KPIs**: Is the product actually faster and more reliable than Word/email workflows?
3. **Adoption KPIs**: Are selected users choosing this tool repeatedly?
4. **Quality/Risk KPIs**: Are we reducing missed scope and operational issues?

### Phase-Gated KPI Targets

| Stage | KPI | Target | Why It Matters |
|------|-----|--------|----------------|
| Build (Weeks 1-6/8) | Planned vs actual hours variance | <= 20% variance weekly | Protects delivery timeline |
| Build (Weeks 1-6/8) | CI pass rate on main branch | >= 95% | Maintains release stability |
| Build (Weeks 1-6/8) | P0/P1 bugs open at phase exit | 0 P0, <= 2 P1 | Ensures quality gates before next phase |
| MVP readiness | End-to-end smoke path success | 100% on required flows | Confirms launch readiness |
| Pilot (first 2-4 weeks) | Weekly active pilot users (selected group) | >= 70% of invited users active weekly | Confirms real usage |
| Pilot (first 2-4 weeks) | Workflow completion rate (project setup -> exhibit export) | >= 80% | Validates usability |

### Core Product Outcome KPIs (Primary)

| Category | KPI | Baseline (Current) | MVP Target | Stretch Target |
|---------|-----|---------------------|------------|----------------|
| Speed | Time to produce first bid-ready exhibit for a trade | ~2-4 hours | <= 90 minutes median | <= 60 minutes median |
| Speed | Time to customize exhibit from existing template | Often 60-120 minutes | <= 45 minutes median | <= 30 minutes median |
| Throughput | Trades scoped per PM per week (comparable project period) | Baseline to capture in first pilot week | +25% vs baseline | +40% vs baseline |
| Quality | Exhibits requiring major rework after PM review | Baseline to capture | <= 20% | <= 10% |
| Quality | Open-question carryover at issuance moment | Baseline to capture | <= 1 per exhibit median | 0 median |
| Reliability | PDF export success rate | N/A | >= 99% | >= 99.5% |

### AI-Specific KPIs

Aligned with privacy decision: only token/cost/error metrics stored, plus acceptance-action metadata.

| KPI | MVP Target | Stretch Target | Notes |
|-----|------------|----------------|-------|
| AI request success rate (non-error response) | >= 97% | >= 99% | Across both generation functions |
| AI timeout/error rate | <= 3% | <= 1% | Should never block manual workflow |
| AI-assisted insertion acceptance rate | >= 60% | >= 75% | % of generated suggestions accepted with minor/no edits |
| Median AI response latency | <= 6s | <= 4s | Per request, user-facing responsiveness |
| AI cost per completed exhibit | <= $2.00 | <= $1.25 | Track for budget control |

### Adoption & Behavior KPIs (Pilot)

| KPI | MVP Target | Why It Matters |
|-----|------------|----------------|
| % of pilot exhibits started from in-app templates | >= 80% | Confirms template library value |
| % of pilot exhibits using notes panel | >= 60% | Confirms notes integration utility |
| % of pilot exhibits using at least one AI action | >= 70% | Confirms AI feature relevance |
| Repeat usage (users creating exhibits in >= 2 separate weeks) | >= 60% of pilot users | Indicates habit formation |
| User satisfaction pulse (1-5) | >= 4.0 average | Fast quality signal during pilot |

### Operational KPIs

| KPI | MVP Target | Notes |
|-----|------------|-------|
| Mean time to detect critical error (MTTD) | < 1 day | Via monitoring/alerts |
| Mean time to resolve P1 production issue (MTTR) | < 2 business days | Pilot reliability target |
| Permission/tenant leakage incidents | 0 | Non-negotiable |
| Data migration failures in deployment | 0 | Release gate check |

### Go / No-Go Criteria After Pilot

Proceed to broader rollout only if all are true:
1. Workflow completion rate is >= 80%.
2. Median first-exhibit time is <= 90 minutes.
3. No permission/tenant isolation incidents occurred.
4. PDF export success is >= 99%.
5. At least 60% of pilot users are repeat weekly users.

If criteria are not met:
- Pause feature expansion.
- Run a 1-2 week stabilization sprint focused only on top friction points and reliability gaps.

### KPI Instrumentation Plan (MVP-Minimal)

Track via lightweight events/logs:
- `project_created`, `trade_imported`, `exhibit_created`, `template_selected`
- `scope_item_added_manual`, `scope_item_added_ai`, `ai_request_success`, `ai_request_error`
- `note_created`, `note_resolved`, `final_review_run`, `pdf_export_success`, `pdf_export_error`
- `exhibit_marked_ready_for_bid`, `exhibit_finalized`

Weekly dashboard review should include:
- Completion funnel (project -> exhibit -> review -> export)
- Time-to-complete medians
- AI cost/error trends
- Top failure points by count

---

## Learning Resources / References

These are selected to match the exact MVP stack and avoid unnecessary rabbit holes.

### Django Core (Architecture, Models, Auth)

- **Django Documentation (start here)**  
  https://docs.djangoproject.com/en/stable/
- **Models & Constraints (for schema integrity)**  
  https://docs.djangoproject.com/en/stable/topics/db/models/  
  https://docs.djangoproject.com/en/stable/ref/models/constraints/
- **Query optimization (`select_related`, `prefetch_related`)**  
  https://docs.djangoproject.com/en/stable/topics/db/optimization/
- **Class-based views + forms (for CRUD speed)**  
  https://docs.djangoproject.com/en/stable/topics/class-based-views/  
  https://docs.djangoproject.com/en/stable/topics/forms/
- **Auth and permissions**  
  https://docs.djangoproject.com/en/stable/topics/auth/default/

### HTMX + Django Patterns (Primary Frontend Interaction)

- **HTMX docs (core attributes/events)**  
  https://htmx.org/docs/
- **HTMX examples**  
  https://htmx.org/examples/
- **django-htmx docs (request helpers, middleware patterns)**  
  https://django-htmx.readthedocs.io/

### PostgreSQL + Migrations

- **Django migrations**  
  https://docs.djangoproject.com/en/stable/topics/migrations/
- **PostgreSQL docs (indexes and constraints)**  
  https://www.postgresql.org/docs/current/indexes.html  
  https://www.postgresql.org/docs/current/ddl-constraints.html

### Testing (Unit, Integration, Lightweight E2E)

- **Django testing docs**  
  https://docs.djangoproject.com/en/stable/topics/testing/
- **pytest-django**  
  https://pytest-django.readthedocs.io/
- **factory_boy (test data factories)**  
  https://factoryboy.readthedocs.io/
- **Playwright Python (smoke E2E)**  
  https://playwright.dev/python/docs/intro

### AI Integration (Claude API + Resilience)

- **Anthropic API docs**  
  https://docs.anthropic.com/
- **Python SDK (Anthropic)**  
  https://github.com/anthropics/anthropic-sdk-python

### PDF Export (MVP)

- **WeasyPrint docs**  
  https://doc.courtbouillon.org/weasyprint/stable/
- **WeasyPrint tutorial/examples**  
  https://doc.courtbouillon.org/weasyprint/stable/tutorial.html

### Deployment & Operations (Simple, Production-Ready MVP)

- **Railway docs**  
  https://docs.railway.com/
- **Render docs**  
  https://render.com/docs
- **Sentry (Django monitoring)**  
  https://docs.sentry.io/platforms/python/guides/django/

### Suggested Study Order (Time-Efficient)

1. Django models/constraints + migrations (before coding Phase 1).
2. HTMX + django-htmx patterns (before Phase 2-3 UI).
3. Django testing + pytest-django + Playwright smoke setup (before Phase 2).
4. Anthropic API docs and SDK usage (before Phase 5).
5. WeasyPrint docs and print CSS examples (before Phase 6).
6. Hosting/monitoring docs only when entering Phase 7.

### Optional, High-Leverage Extras (Only If Needed)

- **Django service-layer patterns (community articles/tutorials)** for keeping business logic out of views.
- **Prompt evaluation templates** (lightweight rubric) to track AI acceptance quality over time.

---

## Implementation Checklist / Next Steps

### Pre-Development Setup

**Environment & Tools**:
- [ ] Install Python 3.11+ and PostgreSQL locally
- [ ] Set up virtual environment tooling (venv or Poetry)
- [ ] Install VS Code or PyCharm with Python/Django extensions
- [ ] Create new private GitHub repository: `scope-of-work-manager`
- [ ] Set up local PostgreSQL database: `scope_manager_dev`

**Knowledge Refresh** (before Phase 1):
- [ ] Review [Django models & constraints docs](https://docs.djangoproject.com/en/stable/topics/db/models/)
- [ ] Skim [HTMX docs](https://htmx.org/docs/) and [examples](https://htmx.org/examples/)
- [ ] Review [django-allauth setup](https://docs.allauth.org/en/latest/installation/quickstart.html)
- [ ] Read [pytest-django quickstart](https://pytest-django.readthedocs.io/en/latest/)

**Design Assets** (optional):
- [ ] Collect 2-3 existing Word scope exhibit examples from past projects
- [ ] Document current company CSI trade list (codes + names used most often)
- [ ] Note current project types used at Hathaway Dinwiddie

---

### Phase 1: Foundation + Data Models (Week 1)

**Django Project Bootstrap**:
- [ ] Create Django project: `django-admin startproject scope_manager`
- [ ] Create 5 Django apps: `core`, `projects`, `exhibits`, `notes`, `reviews`
- [ ] Configure `settings.py`:
  - [ ] PostgreSQL database connection
  - [ ] Install and configure `django-allauth` (email-based auth, disable self-registration)
  - [ ] Add HTMX via CDN in base template
  - [ ] Add Tailwind CSS via CDN
  - [ ] Configure static files
  - [ ] Set `AUTH_USER_MODEL = 'core.User'`
- [ ] Create base template (`templates/base.html`) with nav, flash messages, content block
- [ ] Run initial migration, verify database connection

**Core Models** (`core/models.py`):
- [ ] `Company` model (name, created_at)
- [ ] Custom `User` model extending AbstractBaseUser (email, company FK, role field)
- [ ] `ProjectType` model (name, description)
- [ ] `CSITrade` model (csi_code, name, description)
- [ ] Configure Django admin for all core models
- [ ] Create seed data management command: `python manage.py seed_data`
  - [ ] Seed 6-10 common CSI trades (HVAC, Electrical, Plumbing, Fire Sprinkler, Drywall, Doors, etc.)
  - [ ] Seed 5-6 project types (Office TI, Lab TI, Core & Shell, Seismic Retrofit, Mixed-Use, Other)

**Projects & Exhibits Models**:
- [ ] `projects/models.py`:
  - [ ] `Project` model (company FK, name, number, project_type FK, description, address, created_by FK)
  - [ ] `Trade` model (project FK, csi_trade FK, budget, status, assigned_to FK, order)
  - [ ] Add constraint: unique together on (project, csi_trade)
- [ ] `exhibits/models.py`:
  - [ ] `ScopeExhibit` model (company FK, csi_trade FK, project FK nullable, is_template, scope_description, status, based_on FK, last_edited_by FK, created_by FK)
  - [ ] `ExhibitSection` model (scope_exhibit FK, name, order)
  - [ ] `ScopeItem` model (section FK, parent FK nullable, level, text, original_input nullable, is_ai_generated, order, created_by FK)
- [ ] Configure Django admin for all models
- [ ] Run migrations

**Notes & Reviews Models**:
- [ ] `notes/models.py`:
  - [ ] `Note` model (project FK, primary_trade FK, related_trades M2M, text, note_type, source nullable, status, resolution nullable, resolved_by FK nullable, created_by FK)
- [ ] `reviews/models.py`:
  - [ ] `ChecklistItem` model (company FK, csi_trade FK, text, project_type_tags M2M, created_by FK, source_project FK nullable)
  - [ ] `FinalReview` model (scope_exhibit FK, initiated_by FK, initiated_at, completed_at nullable, status)
  - [ ] `FinalReviewItem` model (final_review FK, check_type, description, status, pm_response nullable, reviewed_at nullable)
- [ ] Configure Django admin for all models
- [ ] Run migrations

**Testing Infrastructure**:
- [ ] Set up pytest + pytest-django:
  - [ ] Create `pytest.ini` config
  - [ ] Create `conftest.py` with database fixtures
- [ ] Install factory_boy, create factories for all models
- [ ] Write model constraint tests (company isolation, unique constraints)
- [ ] Set up GitHub Actions CI: run tests on push

**Phase 1 Polish**:
- [ ] Create company-scoping mixin for querysets
- [ ] Add role helper methods to User model (is_pm, is_pe, etc.)
- [ ] Verify all models appear correctly in Django admin
- [ ] Seed test data: 1 company, 2-3 users (1 PM, 1 PE), CSI trades, project types
- [ ] **Phase 1 exit check**: Auth works, all models migrated, admin can seed data, CI passes, factories create valid test data

---

### Phase 2 Prep: Study Before Starting

Before beginning Phase 2 (Project Dashboard + Trade Setup):
- [ ] Review [Django class-based views](https://docs.djangoproject.com/en/stable/topics/class-based-views/)
- [ ] Review [Django forms](https://docs.djangoproject.com/en/stable/topics/forms/)
- [ ] Read [HTMX attributes reference](https://htmx.org/reference/) (hx-post, hx-get, hx-target, hx-swap)
- [ ] Skim [Tailwind utility classes](https://tailwindcss.com/docs/utility-first) for dashboards/tables

---

### Immediate Next Steps (This Week)

**Do this first**:
1. Complete pre-development setup (environment + tools + GitHub repo)
2. Start Phase 1: Django project bootstrap
3. Build all data models as specified in Technical Architecture section
4. Get CI passing with basic model tests

**Decision point after Phase 1**:
- If Phase 1 took longer than expected (>20 hours), reassess timeline before proceeding
- If Phase 1 went smoothly, proceed directly to Phase 2 (Project Dashboard + Trade Setup)

---

### Getting Unstuck

If you hit blockers during implementation:
- **Django model design questions**: Reference the Technical Architecture section of this document
- **Migration issues**: The models are fully defined in the architecture — implement them exactly as specified
- **Testing setup confusion**: Start with just model tests; add integration tests in Phase 2
- **Time pressure**: The only non-negotiable deliverable for Phase 1 is "all models exist and migrate cleanly" — polish can wait

You can always return with specific questions or blockers as you build. Good luck!

---

## Decision Log

- **2026-03-02**: `is_template` remains in `ScopeExhibit` and is the source-of-truth for template intent. `project` stays nullable and is not used to infer template status.
- **2026-03-02**: Templates can be either global (`project=null`) or attached to company-managed dummy projects used as template buckets by project type/workflow.
- **2026-03-02**: Keep `csi_trade` as the exhibit-to-trade-type link for MVP; do not add `ScopeExhibit.trade` FK yet. Enforce uniqueness on `Trade(project, csi_trade)` to keep joins deterministic.
- **2026-03-03**: MVP delivery target set to fastest realistic timeline (6 weeks best-case at ~20 hrs/week; expected range 6-8 weeks).
- **2026-03-03**: Trade import for MVP is paste-only (CSV upload deferred).
- **2026-03-03**: E2E automation will be lightweight Playwright smoke tests only.
- **2026-03-03**: Pilot will include a few selected users (not solo-only usage).
- **2026-03-03**: AI observability will log token/cost/error metrics only; prompt/response text will not be persisted.

---

## Progress & Learnings

[To be filled as work progresses]

---

*Deep Dive Started: February 24, 2026*
