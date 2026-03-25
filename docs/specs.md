# AI-Powered Scope of Work Manager (Buyout & Subcontract Tool)

*Started: February 24, 2026 · Last Updated: March 3, 2026*

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
- *As a PM, I want to filter trades by status and manager, group them by status or manager, and sort any column so I can focus on the slice of work that needs my attention.*

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
3. PM selects a template. The tool clones it into a new exhibit linked to the project. The editor shows ordered sections (e.g., General Conditions, Scope of Work, Inclusions, Exclusions) with hierarchical scope items inside each.
4. PM customizes the scope:
   - **Edit or delete** items that don't apply (e.g., remove the BIM coordination item if the project doesn't require it)
   - **Add new items** — type in plain language or use the AI to generate exhibit-ready language
   - **Reorder and nest items** using up/down and indent/outdent controls
   - **Use AI at any level**: generate from description (bulk), section AI action (targeted), or per-item rewrite/expand
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

**Post-MVP enhancement**: The AI will also suggest relevant scope items to add or remove based on the scope description (e.g., auto-suggest adding "BMS integration" and "lab exhaust" items for a lab project).

**B) Natural Language → Inclusion/Exclusion Items**

At any point while editing, the PM can type a scope item in plain language and the AI converts it to standardized exhibit language and adds it as an inclusion or exclusion block.

*Example inputs and outputs*:

| PM types (natural language) | AI generates (exhibit language) | Type |
|---|---|---|
| "sub needs to demo existing ceilings in rooms 201-215, keep grid in corridors" | "Demolition and removal of existing acoustical ceiling tile and grid in Rooms 201 through 215 per Drawing A2.1. Existing ceiling grid in corridors to remain; protect in place per Section 024119." | Inclusion |
| "we're not paying them for asbestos abatement" | "Asbestos abatement and remediation of hazardous materials is excluded from this scope of work. Abatement to be performed by Owner's separate contractor prior to commencement of work." | Exclusion |
| "they need to tie into the existing fire alarm panel in the basement" | "Connection and integration to existing fire alarm control panel (FACP) located in Basement Level B1. Provide all wiring, conduit, and programming required for new devices to communicate with existing system." | Inclusion |

The PM can edit the generated text before accepting it.

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

SECTION A: GENERAL CONDITIONS
  A.1  Comply with all applicable codes and regulations
  A.2  Provide all labor, materials, equipment...
  A.3  Coordinate with other trades as required
  A.4  BIM coordination per project BIM Execution Plan
  A.5  LEED documentation requirements
  A.6  Schedule of Values breakdown within 10 days...
  [additional items]

SECTION B: SCOPE OF WORK
  B.1  [Describe what the sub is actually building — quantities, areas, drawing refs]
  B.1.1  [Sub-item detail]

SECTION C: SPECIFIC INCLUSIONS
  C.1  All permits and inspections for this trade
  C.2  [Custom items added per project]

SECTION D: SPECIFIC EXCLUSIONS
  D.1  Fire stopping of own penetrations (by others)
  D.2  [Custom items added per project]

SECTION E: CLARIFICATIONS & ASSUMPTIONS
  E.1  [Owner/architect conversations, design intent notes]
```

**Key design decisions**:
- Templates are structured as **ordered, hierarchical scope items**, not free-form Word docs. Items can be added, deleted, edited, reordered, and nested. This enables: (a) quick customization via AI or direct editing, (b) consistent output format, (c) future AI comparison against specs.
- Output is **PDF** (.pdf) — primary export for sharing, attaching to bids, and uploading to platforms (Procore, BuildingConnected). Teams use Bluebeam for markups/review. All editing happens inside the app, so Word export is not a priority.

**User Stories**:
- *As a PM, I want to see templates ranked by how similar the source project is to my current project so I pick the best starting point.*
- *As a PM, I want to edit, add, and delete scope items rather than rewriting Word docs so customization is faster and the output format is consistent.*
- *As a PE, I want to draft a scope exhibit and have my PM review it in the same tool so we're not emailing Word docs back and forth.*
- *As a PM, I want to describe my project and trade scope in plain English and have the AI generate exhibit-ready language so I don't have to write formal scope language from scratch.*
- *As a PM, I want to type a scope item in natural language and have the AI convert it to a standardized inclusion or exclusion item so the exhibit language is consistent and professional.*

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
   - ⚠️ Flagged as warning — PM sees these but can proceed regardless (MVP is informational only)

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

2. The tool presents a **summary scorecard** — informational, does not block export:
   - ✅ All notes resolved
   - ✅ No cross-trade conflicts
   - ⚠️ 1 custom checklist item flagged — PM should review
   - ⚠️ 2 open questions unresolved — PM should address before issuing

3. PM reviews any flags, then proceeds. The scope exhibit can be exported as PDF at any point — the review is a health check, not a gate. *(Post-MVP: Final Review becomes a blocking gate — see Post-MVP Architecture Notes.)*

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
3. **Template improvement flow** *(Post-MVP)*:
   - PM finishes a project and learned something (e.g., "always include controls interface clause for HVAC on lab projects")
   - PM can **propose** an addition to the company master template
   - Addition is tagged with project type relevance (e.g., "Lab TI only" or "All project types")
   - Over time, master templates get better because they absorb lessons learned from real projects
   - *MVP: lessons learned are seeded by admin only via Django admin. User-submitted proposals with approval workflow are post-MVP.*
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
- Scope editor with hierarchical items (add, edit, delete, reorder, nest)
- **AI scope language assistant** (project description → exhibit language, natural language → inclusions/exclusions, per-item rewrite/expand, section AI, chat)
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
│  │              AI SERVICE LAYER (Claude API)         │ │
│  │  scope gen · rewrite · expand · section AI        │ │
│  │  note-to-scope · completeness · chat w/ tools     │ │
│  └───────────────────────────────────────────────────┘ │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │              PDF EXPORT SERVICE (WeasyPrint)       │ │
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
├── text: text — the exhibit language (may be AI-proposed text when is_pending_review=True)
├── original_input: text (nullable) — what PM typed if AI-generated
├── is_ai_generated: boolean
├── is_pending_review: boolean (default False) — True when item has an unreviewed AI suggestion
├── pending_original_text: text (blank=True) — stores the original text when AI proposes an edit;
│                                               empty string when AI proposed a new item (no original)
├── order: int — display order within siblings at same level
├── created_by (FK → User)
├── created_at
└── updated_at
```

**Pending review semantics**:
- `is_pending_review=True` + `pending_original_text` is non-empty → AI proposed editing an existing item. `text` holds the proposed new text; `pending_original_text` holds the original text so the user can see a diff and reject back to original.
- `is_pending_review=True` + `pending_original_text` is empty → AI proposed a brand-new item. Rejecting deletes the item entirely.
- `is_pending_review=False` → item is live/accepted. Normal state for all manually created or accepted items.

**Creating from a template or past exhibit**: PM selects a starting point (either a template or a finalized past exhibit). The system clones the entire ScopeExhibit — copies the ExhibitSections and all ScopeItems into a new exhibit linked to the project. Sets `based_on` to the source. From that point, it's a fully independent document.

**Saving as template**: PM finishes a project exhibit and wants to save it as a reusable template. The system clones it into a new ScopeExhibit with `is_template=true`. PM can keep `project=null` (global template) or attach it to a company-managed dummy project (project-type template bucket).

**Template selection UI**: "Pick a starting point" shows both templates (`is_template=true`, filtered by `csi_trade`) and past project exhibits (`is_template=false`, `status=FINALIZED`, same `csi_trade`, sorted by project type similarity). No distinction needed in the picker — they're all starting points.

**Trade linkage decision (MVP)**: Keep `csi_trade` on ScopeExhibit and do not add a direct `trade` FK yet. To preserve integrity, enforce one Trade per `(project, csi_trade)` and join exhibits to workflow state through that pair. This keeps the schema simpler while supporting the current buyout lifecycle.

#### Notes Models

```
Note
├── id
├── project (FK → Project)
├── scope_item (FK → ScopeItem, nullable) — when note is linked to a specific scope item (Google Sheets-style comment)
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

**Scope item comments**: When a PM clicks the comment icon on a scope item, the note form pre-links to that item (stored as `scope_item` FK). The note card then renders a reference chip showing the section name and item number, with a "highlight item" button that scrolls to and briefly highlights the item in the editor. Items with linked notes show a comment badge with count. `scope_item` is nullable — notes without a linked item (general trade notes) work exactly as before.

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
| Buyout dashboard | All Trades for a Project; supports multi-value status + manager filters, group-by (status or manager), and sort on any column — all via URL query params, server-rendered with HTMX partial swaps |
| Template / starting point selection | ScopeExhibits where (`is_template=true` OR (`is_template=false` AND `status=FINALIZED`)) AND `csi_trade` matches. Sorted: company master templates first, then past exhibits with exact project type match, then remaining past exhibits by date (most recent first). |
| Scope editor | ScopeExhibit → ExhibitSections (ordered) → ScopeItems per section (ordered, hierarchical) |
| Notes sidebar | Notes where primary_trade = this trade OR this trade in related_trades |
| Project-wide open questions | Notes where project = this project AND note_type = OPEN_QUESTION AND status = OPEN |
| Final review | Automated queries against Notes, ChecklistItems for the trade |

### AI Service Layer

The AI integration is isolated in `ai_services/` and gated by the `AI_ENABLED` setting. Every exhibit workflow works without AI.

**Architecture: "one AI brain, multiple entry points"** — The chat is the full-flexibility interface with all tools available. AI icons throughout the UI (sections, items, notes) are pre-scoped shortcuts into the same service layer. Each icon opens a text input for quick instructions. All AI-generated changes go through the pending review workflow.

#### Service Functions (`ai_services/services.py`)

```python
# Bulk generation: scope description → structured exhibit sections + items
def generate_scope_from_description(exhibit) -> dict

# Single item: natural language → polished scope item text
def generate_scope_item(input_text, exhibit, section) -> str

# Rewrite: existing item + instruction → proposed new text
def rewrite_scope_item(item, exhibit, instruction='') -> str

# Expand: parent item → list of sub-items
def expand_scope_item(item, exhibit) -> list[dict]

# Section AI: free-form instruction scoped to one section → add/edit/delete changes
# Uses Claude tool use API — AI decides the action from the instruction
def section_ai_action(section, exhibit, instruction) -> list[dict]

# Bulk rewrite: all items in a section rewritten with one instruction
# LEGACY — kept for backward compat; superseded by section_ai_action() which uses tool use
def rewrite_section_items(section, exhibit, instruction) -> list[dict]

# Note conversion: note → scope item with overlap detection against existing items
def convert_note_to_scope(note, exhibit, instruction='') -> dict

# Completeness check: identify gaps in scope coverage
def check_exhibit_completeness(exhibit) -> dict

# Conversational chat: multi-turn conversation with tool use
def chat_with_exhibit(exhibit, messages) -> dict

# Streaming chat: yields SSE events for token-by-token rendering
def stream_chat_with_exhibit(exhibit, conversation_history) -> Generator
# yields: ('text_delta', str), ('complete', {full_text, tool_calls}), ('error', str)

# Auto-title: generates a short session title from the first user message
def generate_chat_title(user_message) -> str
```

#### Chat Infrastructure

- **Server-side history**: `ChatSession` + `ChatMessage` models persist conversations across page reloads. Multiple sessions per user per exhibit; lazy creation (session saved on first message send). Auto-titled via `generate_chat_title()` using Claude Haiku.
- **Streaming**: `stream_chat_with_exhibit()` uses the Anthropic SDK's `client.messages.stream()` sync context manager to yield text tokens as they arrive. The view returns a `StreamingHttpResponse` with `content_type='text/event-stream'` (SSE). Text streams token-by-token; tool-call changes are applied after the stream completes.
- **Structured context**: `_build_structured_chat_context()` builds a JSON snapshot of the exhibit state — items with PKs, refs (A.1, A.1.1), hierarchy, pending status, and open notes. Injected into every chat API call.
- **Claude tool use API**: Chat uses `client.messages.stream()` with four tools:
  - `add_scope_item` — add new item to a section (by name)
  - `edit_scope_item` — edit existing item (by PK)
  - `delete_scope_item` — delete existing item (by PK)
  - `convert_note_to_scope` — convert a note into a scope item (by note PK)
- **`_apply_proposed_changes()`** in views handles all tool-generated changes uniformly — creates pending items, sets diffs, resolves notes.

#### AI Models

```
AIRequestLog
├── request_type: SCOPE_FROM_DESCRIPTION | SCOPE_ITEM | REWRITE_ITEM | EXPAND_ITEM |
│                 CHAT | COMPLETENESS_CHECK | REWRITE_SECTION | NOTE_TO_SCOPE
├── exhibit (FK → ScopeExhibit, nullable)
├── success: boolean
├── error_message: text (blank)
├── tokens_used: int (nullable)
├── latency_ms: int (nullable)
└── created_at

ChatSession
├── exhibit (FK → ScopeExhibit, nullable)
├── user (FK → User)
├── title: varchar(200), nullable — auto-generated from first message via Claude Haiku
├── context_type: default 'exhibit'
├── created_at
└── updated_at

ChatMessage
├── session (FK → ChatSession)
├── role: 'user' | 'assistant'
├── content: text
├── user (FK → User, nullable — null for assistant)
├── changes_applied_pks: JSONField (default=[]) — PKs of scope items created/edited by this message
├── tokens_used: int (nullable)
└── created_at
```

#### Prompt Strategy

System prompts in `ai_services/prompts.py` include:
- Shared `_LANGUAGE_RULES` (capitalize trade names, use "provide and install", reference drawings as "per the Contract Documents", imperative mood)
- Function-specific instructions and output format requirements
- Trade/project/section context injected at call time

**Pending review workflow** (applies to all AI-generated suggestions):
1. AI functions create or modify `ScopeItem` records with `is_pending_review=True`
2. The editor shows a **pending banner** when any items have `is_pending_review=True`, displaying the count and bulk "Accept All" / "Reject All" buttons
3. Each pending item renders with a **side-by-side diff**: original text crossed out in red, proposed text highlighted in green
4. Per-item **Accept ✓** and **Reject ✗** buttons:
   - Accept → clears `is_pending_review`, keeps `text` as-is, clears `pending_original_text`
   - Reject → if `pending_original_text` is non-empty: restore original `text`, clear pending state; if empty (new item): delete the item
5. PM can also edit the proposed text directly before accepting (edit-then-accept)

**System prompt strategy**: Each function uses a system prompt that includes:
- Trade-specific terminology and conventions
- Standard exhibit formatting rules (capitalize trade names, reference drawings as "per Drawing X.X", use "provide and install" not "supply")
- Legal/contractual tone guidelines
- The current exhibit content to avoid duplication and enable completeness checks

**API choice**: Claude API (Sonnet for speed/cost — structured text generation). Falls back gracefully if API is unavailable — PM can always type exhibit language manually.

### AI Assistant UX

The AI is surfaced through multiple entry points in the scope editor, all using the ✨ icon:

#### 1. Scope Description AI (bulk generation)
- ✨ button in the scope description card (editor header area)
- Triggers `generate_scope_from_description()` — generates sections + items from the description
- All generated items created as `is_pending_review=True` for batch review
- Gap-fill mode: if exhibit already has substantial content (≥5 items), AI identifies missing items rather than regenerating everything

#### 2. Section AI (unified section-level action)
- ✨ icon in section header (visible on hover) — opens a popover with a single text input
- PM types any instruction: "add an exclusion for GC work", "rewrite in subcontract language", "expand the first item"
- AI determines the action (add, edit, delete, or any combination) via tool use API
- All changes created as pending review items

#### 3. Item AI (per-item rewrite + expand)
- ✨ icon on each scope item (visible on hover) — opens an inline popover
- "Rewrite" with optional instruction text input
- "Expand into sub-items" button
- Both create pending review items

#### 4. Note-to-Scope Conversion
- ✨ icon on each open note card — opens an inline form (bottom of card)
- Checks for overlap against existing scope items before creating
- If overlap detected: shows overlap banner with "Edit Existing Item" / "Add New Anyway" / dismiss options
- If no overlap: creates pending scope item and auto-resolves the note
- Also available via chat tool for batch conversion ("convert all notes to scope")

#### 5. Chat Side Panel (conversation + all tools)
- "Chat with AI ✨" button in the editor header expands the right panel to 45vw
- Layout (top to bottom): header with session dropdown, collapsible Quick Actions (completeness check), chat messages area, input area
- **Multi-session**: Users can have multiple chat sessions per exhibit. Session dropdown in header allows new chat, switch, rename, and delete. Sessions are lazy-created (saved on first message send) and auto-titled via Claude Haiku.
- **Streaming responses**: Chat uses SSE (`StreamingHttpResponse` with `text/event-stream`). Text appears token-by-token as Claude generates it. Vanilla JS `fetch()` + `ReadableStream` on the client (HTMX cannot handle SSE streaming). Three SSE event types: `text_delta` (incremental text), `error`, `done` (final linkified text + tool-call results).
- **Thinking timer**: A live counter next to the typing dots shows elapsed seconds during generation (updates every 1s). On completion, shows "Thought for Xs" below the response.
- **Chat messages**: scrollable history with user/assistant bubbles. User bubble appended immediately on submit; assistant bubble shows 3-dot bouncing typing indicator until first token arrives, then streams text with auto-scroll.
- **Input area**: textarea with context chip picker (`+` button to attach sections/notes as context), Send button with animated spinner during generation
- **Tool use**: AI can add/edit/delete items and convert notes to scope via Claude tool use API. Tool-call changes are applied after the stream completes. All changes applied as pending review. `pendingChanged` event dispatched to `document.body` to refresh section list and pending banner.
- **Completeness check**: results render as a chat-style bubble with actionable gap cards ("+ Add to {section}" / "✕ Dismiss")
- **Loading indicators**: All AI action buttons (Generate Scope, Section AI, item rewrite/expand, note-to-scope, completeness check) use animated SVG spinners instead of static indicators

#### Pending Banner
- Shown in the editor header when `exhibit.sections.items.filter(is_pending_review=True).exists()`
- Displays: "N AI suggestion(s) pending review" with "Accept All" and "Reject All" buttons
- Updated via HTMX `HX-Trigger: pendingChanged` header after any accept/reject action

#### Pending Item Display
Each item with `is_pending_review=True` renders differently in `item.html`:
- If `pending_original_text` is non-empty (edit): strikethrough original in red, new text in green below
- If `pending_original_text` is empty (new item): new text highlighted in amber/yellow background
- Accept ✓ button: `hx-post` → `item_accept_ai` view → returns normal item partial
- Reject ✗ button: `hx-post` → `item_reject_ai` view → returns normal item (restored) or empty (deleted)

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
| Add note linked to scope item | click comment icon → JS sets hidden `scope_item_id` field → same `hx-post` → note saved with scope_item FK → returns updated notes list |
| AI: generate scope from description | `hx-post` → calls Claude API → creates items with `is_pending_review=True` → returns section list + pending banner (with loading indicator) |
| AI: section AI action | `hx-post` with instruction → calls Claude with tool use API → applies add/edit/delete changes as pending → returns section item list; fires `HX-Trigger: pendingChanged` |
| AI: rewrite item | `hx-post` → calls Claude API → sets `is_pending_review=True`, `pending_original_text`, updates `text` → returns updated item partial (diff view) + pending banner |
| AI: expand item into sub-items | `hx-post` → calls Claude API → creates child items with `is_pending_review=True` → returns section item list + pending banner |
| AI: note-to-scope conversion | `hx-post` → calls Claude API → overlap check → returns overlap banner (with edit/add/dismiss) or creates pending item + resolves note → returns updated note card |
| AI: completeness check | `hx-post` → calls Claude API → returns chat-bubble partial appended to `#chat-messages` with gap cards (accept/dismiss per card, client-side) |
| AI: add gap item | `hx-post` → creates pending `ScopeItem` in target section → returns section item list; fires `HX-Trigger: pendingChanged`; card replaced with "✓ Added" in-place |
| AI: chat send (side panel) | Vanilla JS `fetch` → `StreamingHttpResponse` (SSE). Server streams `text_delta` events token-by-token, then `done` event with linkified text + `changes_applied_pks`. Client appends user bubble immediately, streams text into assistant bubble, applies tool-call changes on `done`, dispatches `pendingChanged` event to body |
| AI: accept pending item | `hx-post` → clears pending fields → returns normal item partial; fires `HX-Trigger: pendingChanged` |
| AI: reject pending item | `hx-post` → restores original or deletes item → returns item partial or empty; fires `HX-Trigger: pendingChanged` |
| AI: accept all pending | `hx-post` → bulk clears pending on all items in exhibit → returns section list + clears banner |
| AI: reject all pending | `hx-post` → bulk restores/deletes all pending items → returns section list + clears banner |
| Dashboard filter/group/sort | `hx-get` with URL params (`status[]`, `assigned_to[]`, `group`, `sort`, `dir`) → returns `#dashboard-content` partial; `hx-push-url="true"` keeps URL bookmarkable |
| Dashboard inline status/assign (grouped mode) | `hx-post` with current filter+group state in `hx-vals` → returns full `#trades-table-body` innerHTML so row moves to correct group immediately; fires `HX-Trigger: statsChanged` |
| Change trade status | `hx-post` → updates Trade.status → returns updated dashboard row (flat mode) or full tbody (grouped mode) |
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

**3. AI-Powered Boilerplate Toggle Suggestions & Template/Item Recommendations**
- MVP: PM manually selects a template/past exhibit as starting point, and manually adds/edits items with AI language assistance. Boilerplate items are toggled manually.
- Post-MVP: the AI uses the `scope_description` field (and `project.description` for broader context) to:
  - **Suggest boilerplate toggles**: based on the scope description, auto-suggest which boilerplate items to enable/disable (e.g., auto-enables "BMS integration" and "lab exhaust" for a lab project, disables "new AHU installation")
  - **Recommend starting points**: rank templates and past exhibits by relevance to the current scope description (semantic similarity, not tags)
  - **Suggest scope items**: based on the scope description, suggest new items or modifications to existing items within the exhibit (e.g., "This is a lab project — consider adding fume hood exhaust connections to your HVAC scope")
  - **Flag missing scope**: compare scope description against the current exhibit and surface gaps (e.g., "You mentioned BMS integration but no scope item addresses controls coordination")
- Implementation: additional Claude API calls that take the scope description + project description + current exhibit state and return suggestions. Displayed as a sidebar or inline suggestions the PM can accept/dismiss.
- No data model changes needed — suggestions are transient (generated on demand, not stored)

**4. Project Membership & Invitations**
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

**5. Blocking Review Workflow**
- MVP: Final Review is informational — PM sees warnings but nothing is blocked from being issued
- Post-MVP: Final Review becomes a gate. Changes:
  - FinalReview status expands: `IN_PROGRESS | COMPLETED | PASSED | PASSED_WITH_OVERRIDES | BLOCKED`
  - Add `is_override: boolean` to FinalReviewItem — distinguishes "PM confirmed this is addressed" (PASS) from "PM acknowledged but is overriding" (override with justification in `pm_response`)
  - PM must resolve or override all FAIL items before exhibit can move to `READY_FOR_BID`
  - Overall status derived: all PASS → `PASSED`, any overrides → `PASSED_WITH_OVERRIDES`, unresolved FAILs → `BLOCKED`

**6. User-Submitted ChecklistItems with Approval Workflow**
- MVP: ChecklistItems are admin-seeded only (via Django admin). No user-facing creation UI.
- Post-MVP: PM/PE can submit new ChecklistItems from the app UI. Add `status: PENDING | APPROVED` field to ChecklistItem. New items created with `status = PENDING`. Admin reviews and approves via Django admin (or a simple approval view). During Final Review, only `APPROVED` items are pulled. No structural model changes — just one field, a queryset filter, and the submission UI.

**7. Additional Model Fields (Deferred)**
- `Trade.spec_section`: text (nullable) — reference to the relevant spec section number (e.g., "23 21 13"). Useful when AI spec reading is added in V2 to link trades to their spec sections.
- `Trade.bid_due_date`: date (nullable) — when bids are due for this trade. Enables dashboard sorting/filtering by urgency. Currently tracked in BuildingConnected, so this would be a convenience duplicate.
- `Project.status`: ACTIVE | COMPLETED | ARCHIVED — allows archiving old projects so they don't clutter the dashboard. Archived projects remain searchable for template reuse but don't appear in the active project list.

---

## Tech Stack & Rationale

| Technology | Purpose | Why This Choice |
|-----------|---------|-----------------|
| **Django 5.2** | Web framework | Proven, batteries-included framework. ORM handles the relational data model well. Built-in auth, admin, forms. |
| **PostgreSQL** | Database | Production-grade relational DB. Handles the structured data model (projects → trades → scopes → items). Django's best-supported DB. |
| **HTMX** | Dynamic UI | No JavaScript framework needed. Server-rendered HTML with dynamic behavior (toggles, notes, AI responses) without a JS framework. |
| **Claude API (Sonnet)** | AI scope generation | Fast and cost-effective for structured text generation. Strong at following formatting instructions and maintaining professional tone. AI service layer is abstracted — model can be swapped. |
| **WeasyPrint** | PDF export | Converts HTML/CSS → PDF using Django templates — no new tooling or skill set required. Good typography and page control. |
| **Tailwind CSS** | Styling | Utility-first CSS. Fast to build professional UI without writing custom CSS. Good component patterns for dashboards, forms, editors. |
| **django-allauth** | Authentication | Handles login/logout/change-password pages. **Self-registration disabled** — admin creates user accounts via Django admin (email, name, company, role, password). Post-MVP: add invite flow via SendGrid or similar. |
| **Railway** | Hosting | Docker-based deployment from Git. PostgreSQL included. Auto-deploy on push to `main`. |

### Alternatives Considered

| Alternative | Why Not |
|------------|---------|
| **React/Next.js frontend** | Adds complexity (separate frontend app, API layer, deployment). HTMX achieves the needed interactivity without a JS framework. |
| **GPT-4 / OpenAI API** | Claude Sonnet is comparable for this task. Could swap later if needed — AI service layer is abstracted. |
| **python-docx (Word export)** | Initially considered for Word output, but since editing happens in-app, PDF is the primary export. Eliminates dependency. Can add Word export later if users request it. |
| **ReportLab (PDF)** | Lower-level than WeasyPrint. Would require more code to achieve the same layout. WeasyPrint lets us reuse HTML/CSS skills. |
| **SQLite** | Fine for local dev, but PostgreSQL is needed for multi-user production deployment. Start with PostgreSQL from day one to avoid migration pain. |

---

## Pending Implementation

Use this section as the backlog. When starting new work, pull items into a versioned phase in `docs/checklist.md`.

### Bugs

*No known bugs at this time.*

### Pending Features

#### Production Hardening

- [ ] **`SECURE_REFERRER_POLICY`** — Not yet set in production settings
- [ ] **Fail-loudly env var validation** — `SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS` currently have insecure fallbacks; should raise `ImproperlyConfigured` if missing in production
- [ ] **Custom 404/500 error pages** — Branded templates instead of Django defaults
- [ ] **Password reset email** — Configure real email backend (SendGrid, SES, or SMTP)
- [ ] **Rate limiting on AI endpoints** — Per-user rate limits on AI views (`django-ratelimit`)
- [ ] **Claude API timeout** — Explicit timeout (30-60s) with graceful error handling
- [ ] **Seed production data** — Management command for initial company, admin user, trade templates, checklist items
- [ ] **Pilot launch onboarding** — 2-3 PMs + PEs, brief onboarding guide, weekly check-ins

#### App Quality of Life

- [ ] **Confirmation dialogs on destructive actions** — JS confirm or modal before delete operations
- [ ] **Project list search/filter** — Filter by name, number, status, assigned PM
- [ ] **Finalized exhibit lock** — Read-only editor or explicit "unlock" action for finalized exhibits
- [ ] **Application logging** — Loggers per app, user actions at INFO, errors at ERROR
- [ ] **Loading state clarity** — Verify all AI actions have loading indicators, buttons disabled during requests
- [ ] **Sentry context enrichment** — User/company breadcrumbs for debugging
- [ ] **Pagination** — Project list, template picker, notes lists
- [ ] **Audit trail** — `last_modified_by` + `modified_at` on key models
- [ ] **User management UI** — In-app admin panel for company admins
- [ ] **Concurrent edit warning** — "Last edited by X, Y minutes ago" with stale save warning
- [ ] **Undo / soft delete** — "Recently deleted" recovery for scope items and sections
- [ ] **Mobile/tablet responsiveness** — Sidebar layout adaptation for iPads
- [ ] **Keyboard shortcuts** — Enter-to-save, Tab-to-next-item, Escape-to-cancel
- [ ] **Database backup strategy** — Verify and document Railway recovery process
- [ ] **Async PDF generation** — Background task for large exhibits

#### AI

- [ ] **Differentiated Error Messages** — Distinguish rate-limited, context-too-long, timeout, and unavailable errors
- [ ] **Cost Visibility Dashboard** — Admin view showing AI usage metrics from `AIRequestLog`
- [ ] **AI Result Caching** — Hash-based caching of read-only AI results with TTL and invalidation on exhibit writes
- [ ] **Few-Shot Examples in Prompts** — Add 2-3 concrete input/output examples to each system prompt
- [ ] **Company-Configurable Language Rules** — `scope_language_rules` on Company model, injected into prompts alongside `_LANGUAGE_RULES`
- [ ] **Project-Type-Specific Prompt Context** — Domain knowledge per ProjectType (e.g., lab TI → fume hoods, BMS integration)
- [ ] **Accept/Reject Feedback Loop** — Track accept/reject signals per AI-generated item; surface acceptance rate analytics
- [ ] **Cross-Trade Gap/Overlap Detection** — Analyze scopes across all trades to find unassigned work and duplicate scope. Project-level view from buyout dashboard; findings convertible to Notes or ScopeItems
- [ ] **Smart Template Ranking** — AI-ranked template recommendations based on scope description, project type, and template content
- [ ] **Spec PDF Reading & Comparison** — Upload project spec PDFs, extract relevant trade sections, compare against current exhibit to flag deviations
- [ ] **Exhibit Comparison/Diff** — Compare two exhibits side-by-side to identify differences
- [ ] **Scope Language Standardization Pass** — AI pass to normalize language across an entire exhibit
- [ ] **Enhanced Observability** — `AIToolCallLog` model tracking individual tool calls within a request
- [ ] **Multi-Step Autonomous Scope Building** — Agent loop with human checkpoints at key decision points
- [ ] **Context Window Management** — Token counting, summarization, exhibit context compression
- [ ] **Tool Use Safety Layer** — Per-turn limits, confirmation for destructive actions, rate limiting per session

#### Future Features

- [ ] **Drag-and-Drop Reordering** — Add Sortable.js (~2KB) alongside HTMX. Same backend endpoint, richer interaction
- [ ] **Track Changes** — `ScopeItemHistory` model logging every edit. "Review Changes" view with diffs for PM approval
- [ ] **Project Membership & Invitations** — `ProjectMember` through-table with roles (PM, PE, view-only)
- [ ] **Blocking Review Workflow** — Final Review becomes a gate before `READY_FOR_BID`
- [ ] **User-Submitted Checklist Items** — PMs submit ChecklistItems with approval workflow
- [ ] **Additional Model Fields** — `Trade.spec_section`, `Trade.bid_due_date`, `Project.status` (ACTIVE/COMPLETED/ARCHIVED)


---

## Success Metrics / KPIs

Reference targets for pilot evaluation.

### Product Outcome KPIs

| Category | KPI | Baseline | Target | Stretch |
|---------|-----|----------|--------|---------|
| Speed | Time to produce first bid-ready exhibit for a trade | ~2-4 hours | <= 90 min median | <= 60 min |
| Speed | Time to customize exhibit from existing template | 60-120 min | <= 45 min median | <= 30 min |
| Throughput | Trades scoped per PM per week | Capture in first pilot week | +25% vs baseline | +40% |
| Quality | Exhibits requiring major rework after PM review | Capture baseline | <= 20% | <= 10% |
| Quality | Open-question carryover at issuance | Capture baseline | <= 1 per exhibit | 0 |
| Reliability | PDF export success rate | N/A | >= 99% | >= 99.5% |

### AI KPIs

| KPI | Target | Stretch |
|-----|--------|---------|
| AI request success rate | >= 97% | >= 99% |
| AI timeout/error rate | <= 3% | <= 1% |
| AI suggestion acceptance rate | >= 60% | >= 75% |
| Median AI response latency | <= 6s | <= 4s |
| AI cost per completed exhibit | <= $2.00 | <= $1.25 |

### Adoption KPIs (Pilot)

| KPI | Target |
|-----|--------|
| Exhibits started from in-app templates | >= 80% |
| Exhibits using notes panel | >= 60% |
| Exhibits using at least one AI action | >= 70% |
| Repeat users (active in >= 2 separate weeks) | >= 60% of pilot users |
| User satisfaction pulse (1-5) | >= 4.0 average |

---

## Decision Log

- **2026-03-02**: `is_template` remains in `ScopeExhibit` and is the source-of-truth for template intent. `project` stays nullable and is not used to infer template status.
- **2026-03-02**: Templates can be either global (`project=null`) or attached to company-managed dummy projects used as template buckets by project type/workflow.
- **2026-03-02**: Keep `csi_trade` as the exhibit-to-trade-type link for MVP; do not add `ScopeExhibit.trade` FK yet. Enforce uniqueness on `Trade(project, csi_trade)` to keep joins deterministic.
- **2026-03-03**: Trade import is paste-only (CSV upload deferred).
- **2026-03-03**: AI observability logs token/cost/error metrics only; prompt/response text is not persisted.
