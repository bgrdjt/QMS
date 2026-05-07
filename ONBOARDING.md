# QMS Document Management System — Complete Guide

**Welcome!** This guide explains everything about this Quality Management System from scratch, assuming you've never seen it before.

---

## Table of Contents

1. [What This System Is](#what-this-system-is)
2. [What Problem It Solves](#what-problem-it-solves)
3. [Understanding GitHub Codespaces](#understanding-github-codespaces)
4. [System Architecture](#system-architecture)
5. [Getting Started](#getting-started)
6. [Daily Development Workflow](#daily-development-workflow)
7. [What The Tests Test](#what-the-tests-test)
8. [How Versioning Works](#how-versioning-works)
9. [How To Iteratively Improve](#how-to-iteratively-improve)
10. [Where Documentation Goes](#where-documentation-goes)
11. [How Everything Functions Together](#how-everything-functions-together)
12. [Real-World Deployment](#real-world-deployment)
13. [Common Scenarios](#common-scenarios)
14. [Troubleshooting](#troubleshooting)

---

## What This System Is

**QMS DMS** (Quality Management System - Document Management System) is a **self-contained, script-powered document control system** for small medical device companies. Think of it like a custom-built version of expensive platforms like Greenlight Guru or MasterControl, but:

- **No subscription fees** — you own the code
- **No vendor lock-in** — runs on your infrastructure
- **Customizable** — you control every feature
- **Standards compliant** — ISO 13485, ISO 9001, ISO 14971, FDA QMSR

### What It Does

It manages the **entire lifecycle** of controlled documents:

```
DRAFT → IN_REVIEW → APPROVED_PENDING → EFFECTIVE → OBSOLETE
```

For each document, it tracks:
- **Unique ID** (SOP-001, RM-005, etc.)
- **Version/Revision** (RevA, RevB... then Rev1, Rev2...)
- **Status** (where in the lifecycle)
- **Owners and approvers**
- **Review/approval routing**
- **Change requests** (why it changed)
- **Audit trail** (who did what when)
- **Review due dates** (annual review requirements)

### Who Uses It

- **Authors** — create and edit documents
- **Reviewers** — technical review before approval
- **Approvers** — QA Lead signs off (makes EFFECTIVE)
- **Auditors** — inspect the system during audits

---

## What Problem It Solves

### The Problem

Medical device companies need **document control** to comply with regulations:

- FDA requires you prove you follow your procedures
- ISO 13485 requires controlled documents with version tracking
- Auditors need to see who approved what and when
- Change control requires proving changes were reviewed

**Without a system:**
- Documents scattered across shared drives
- No version tracking (Document_v3_final_FINAL_USE_THIS.docx)
- No audit trail
- Manual routing via email
- Risk of using obsolete procedures

**With this system:**
- Every document has a unique ID and version
- Full audit trail stored in JSON logs
- Automated routing to reviewers/approvers
- One source of truth for EFFECTIVE documents
- Notifications when review is due

---

## Understanding GitHub Codespaces

### What Is Codespaces?

**GitHub Codespaces** is a **cloud-based development environment**. Instead of installing Python, Flask, and all dependencies on your local computer, you get a **pre-configured Linux container in the cloud** with everything already set up.

Think of it like this:

| Traditional Development | With Codespaces |
|------------------------|-----------------|
| Install Python on your Windows machine | Already installed in the cloud |
| Install Flask, libraries manually | Already installed automatically |
| "Works on my machine" problems | Everyone gets identical environment |
| Limited to one computer | Work from anywhere with a browser |

### How It Works

1. **You click "Code → Open with Codespaces" on GitHub**
2. **GitHub creates a Linux container for you** (Ubuntu 24.04)
3. **It reads `.devcontainer/devcontainer.json`** to see what to install
4. **It automatically runs `pip install -r requirements.txt`**
5. **You get VS Code in your browser** with a terminal, file editor, everything
6. **Port 5151 gets forwarded** so you can access your Flask server

### Why Codespaces for This Project?

- **Backend server** — The Flask API runs perfectly in a Linux environment
- **No Windows headaches** — No PATH issues, no "Python not found" errors
- **Team consistency** — Everyone gets the same Python version, same libraries
- **Quick onboarding** — New developers start coding in 2 minutes, not 2 hours
- **Separate from client machines** — The server runs centrally; client machines just run the desktop app

### What Runs Where

```
┌─────────────────────────────────────────────────────────┐
│  CODESPACES (Cloud Linux Container)                     │
│                                                          │
│  ✓ Flask server (dms_server.py) on port 5151           │
│  ✓ Python 3.12                                          │
│  ✓ All dependencies auto-installed                      │
│  ✓ Development tools (make, curl, git)                  │
│  ✓ Your code editor (VS Code in browser)                │
│                                                          │
│  → You edit Python files here                           │
│  → You test the API here                                │
│  → You commit and push from here                        │
└─────────────────────────────────────────────────────────┘
                           ↕ API calls (HTTP)
┌─────────────────────────────────────────────────────────┐
│  CLIENT MACHINE (Windows/Mac)                           │
│                                                          │
│  ✓ Desktop app (qms_app.py) — the GUI                   │
│  ✓ Microsoft Word with QMS Ribbon                       │
│  ✓ QMS Root folder (network drive or local)             │
│                                                          │
│  → Users interact with GUI                              │
│  → Word documents stored here                           │
│  → Register and audit log stored here                   │
└─────────────────────────────────────────────────────────┘
```

**Key insight:** Codespaces is where you **develop the backend**. Client machines are where you **deploy the full system** (GUI + API + documents).

---

## System Architecture

### The Big Picture

```
┌──────────────────────────────────────────────────────────────────┐
│  USER INTERFACE LAYER                                            │
│                                                                   │
│  • Desktop App (qms_app.py) — PyQt5 GUI with buttons/tables     │
│  • Word Ribbon — 16 buttons embedded in Microsoft Word           │
│  • Excel Ribbon — Risk register tools in Excel                   │
│                                                                   │
│  All UI sends HTTP requests to ↓                                 │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│  API LAYER (Flask Server on port 5151)                          │
│                                                                   │
│  server/dms_server.py:                                           │
│    • GET  /documents          → list all documents               │
│    • POST /documents/new      → create new document              │
│    • POST /documents/ID/promote → advance lifecycle              │
│    • GET  /cr                 → list change requests             │
│    • POST /routing/submit-review → route to reviewers            │
│    • GET  /roster             → team members                     │
│                                                                   │
│  server/routing_engine.py:                                       │
│    • Review/approval routing logic                               │
│    • Notification queue management                               │
│    • Team roster with role history                               │
│                                                                   │
│  server/cr_engine.py:                                            │
│    • Change Request lifecycle                                    │
│    • Link documents to CRs                                       │
│    • Approve/make-effective workflows                            │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│  DATA LAYER (QMS Root Folder)                                   │
│                                                                   │
│  _REGISTER/                                                      │
│    • document_register.csv    — master list of all documents     │
│    • audit_log.json           — who did what when                │
│    • team_roster.json         — members, roles, role history     │
│    • review_queue.json        — pending reviews/approvals        │
│    • change_requests.json     — all CRs and their status         │
│    • notifications.json       — notification inbox               │
│                                                                   │
│  01_QUALITY_MANUAL/, 02_SOPs/, ... 11_CHANGE_REQUESTS/          │
│    └─ Draft/, InReview/, Effective/, Obsolete/                  │
│         └─ SOP-001_Rev2_Document_Control_EFFECTIVE.docx         │
│                                                                   │
│  INFORMAL_DOCS/                                                  │
│    └─ Documents not under QMS control                           │
│                                                                   │
│  _ARCHIVE/                                                       │
│    └─ Old EFFECTIVE versions when new version goes live         │
└──────────────────────────────────────────────────────────────────┘
```

### Key Concepts

**1. Stateless API**
- The Flask server has no database
- All data lives in CSV/JSON files in the QMS Root folder
- The server reads files, modifies them, writes them back

**2. Single Source of Truth**
- `document_register.csv` is the master list
- Every document operation updates the register
- The register is the only thing you need to back up

**3. Folder-Based Organization**
- Documents stored in folders by type (01_QUALITY_MANUAL, 02_SOPs, etc.)
- Subfolders by lifecycle state (Draft, InReview, Effective, Obsolete)
- File naming convention: `{DOC_ID}_Rev{VERSION}_{TITLE}_{STATUS}.docx`

**4. Audit Trail**
- Every action appends to `audit_log.json`
- Format: `{timestamp, action, doc_id, user, details}`
- Immutable log (never delete, only append)

---

## Getting Started

### First Time Setup (Takes 2 Minutes)

**1. Open This Repository in Codespaces**

- Go to https://github.com/bgrdjt/QMS
- Click the green **Code** button
- Click **Codespaces** tab
- Click **Create codespace on main**
- Wait 60 seconds while it builds

**2. Install Dependencies**

Once Codespaces opens, you'll see a terminal. Type:

```bash
make setup
```

This installs Flask, reportlab, pypdf, etc. (Takes 15 seconds)

**3. Create Test Environment**

```bash
make env
```

This creates a fake QMS folder called `TEST_QMS/` with:
- 7 sample documents
- 3 team members (QA Lead, Tech Reviewer, Dev User)
- 2 projects (PRJ-001 Cardiac Monitor, PRJ-002 Infusion Pump)
- Audit log with 8 events
- Change request for SOP-001

**4. Start The Server**

```bash
make dev
```

You'll see:
```
QMS DMS Server v1.4 — http://localhost:5151
 * Running on http://0.0.0.0:5151
 * Restarting with stat
 * Debugger is active!
```

Codespaces will pop up a notification: **"Your application is available on port 5151"**. Click **Open in Browser**.

**5. Test It**

Open a **second terminal** (click the + button in the terminal pane):

```bash
make ping
```

You should see:
```json
{
  "status": "ok",
  "version": "1.4"
}
```

**Congratulations!** The system is running. Now let's explore what you can do.

---

## Daily Development Workflow

### The Hot-Reload Loop

This is **exactly like web development** with `npm run dev`, but for a Python backend:

**Terminal 1 (The Server)**
```bash
make dev
```
- Server starts with **auto-reload enabled**
- Every time you **save a Python file**, it restarts automatically
- You don't need to stop and restart manually

**Terminal 2 (Testing While You Code)**
```bash
make stats          # See document counts
make docs           # See all documents
make register       # Pretty table view
make test-all       # Run full test suite
```

**Your Workflow:**

1. Edit `server/dms_server.py` (add a new endpoint)
2. Save the file
3. Terminal 1 shows: `Restarting with stat...`
4. In Terminal 2, test your new endpoint: `curl http://localhost:5151/your-new-endpoint`
5. Repeat until it works
6. Commit: `git add . && git commit -m "Added new endpoint"`
7. Push: `git push`

### Example: Adding a New Feature

**Scenario:** You want to add a `/documents/overdue` endpoint that lists documents past their review date.

**Step 1: Edit the code**

Open `server/dms_server.py`, scroll to the bottom, add:

```python
@app.route("/documents/overdue", methods=["GET"])
def overdue_documents():
    try:
        rows = load_register()
        today = datetime.date.today()
        overdue = []
        for r in rows:
            if r.get("next_review_date") and r["status"] == "EFFECTIVE":
                review_date = datetime.date.fromisoformat(r["next_review_date"])
                if review_date < today:
                    overdue.append(r)
        return jsonify(overdue)
    except Exception as e:
        return error_json(str(e))
```

**Step 2: Save the file**

Press `Ctrl+S`. Terminal 1 will show the server restarting.

**Step 3: Test it**

In Terminal 2:
```bash
curl http://localhost:5151/documents/overdue | python -m json.tool
```

**Step 4: Add a Makefile shortcut**

Edit `Makefile`, add:
```makefile
overdue:
	@curl -s http://localhost:5151/documents/overdue | python -m json.tool
```

Now you can just type `make overdue`.

**Step 5: Commit**

```bash
git add server/dms_server.py Makefile
git commit -m "Added /documents/overdue endpoint"
git push
```

**Done!** That's the iterative improvement cycle.

---

## What The Tests Test

### Test Philosophy

The tests validate **real workflows** that users perform:

1. **Create a document** (DRAFT status)
2. **Route it for review** (DRAFT → IN_REVIEW)
3. **Complete the review** (IN_REVIEW → APPROVED_PENDING or back to DRAFT if rejected)
4. **Make it effective** (APPROVED_PENDING → EFFECTIVE)

### Test Breakdown

**`make test-new-doc`** — Creates a new document

**What it does:**
```bash
curl -X POST http://localhost:5151/documents/new \
  -H "Content-Type: application/json" \
  -d '{"doc_type":"SOP","title":"Test Procedure","owner":"Dev User"}'
```

**What it tests:**
- ✓ Next doc ID generation (SOP-004, SOP-005, etc.)
- ✓ Document register gets updated
- ✓ File path is created in correct folder (02_SOPs/Draft/)
- ✓ Status starts as DRAFT
- ✓ Audit log records DOC_CREATED

**`make test-lifecycle`** — Full document lifecycle

**Step 1: Create document**
- Creates SOP with title "Lifecycle Test"
- Stores doc_id in temp file

**Step 2: Submit for review**
```bash
curl -X POST http://localhost:5151/routing/submit-review \
  -d '{"doc_id":"SOP-XXX","reviewers":[...]}'
```
- ✓ Status changes DRAFT → IN_REVIEW
- ✓ Routing record created in review_queue.json
- ✓ Notification sent to Tech Reviewer
- ✓ Audit log records SUBMITTED_FOR_REVIEW

**Step 3: Complete review**
```bash
curl -X POST http://localhost:5151/routing/complete-review \
  -d '{"route_id":"...","reviewer_name":"Tech Reviewer","notes":"Approved"}'
```
- ✓ Routing record marked complete
- ✓ Notification sent back to document owner
- ✓ Status remains IN_REVIEW (ready for approval step)
- ✓ Audit log records REVIEW_COMPLETED

**What it doesn't test yet (but should):**
- Approval step (IN_REVIEW → APPROVED_PENDING)
- Make-effective step (APPROVED_PENDING → EFFECTIVE)
- Change request workflow
- Rejection scenarios

### How to Add More Tests

**1. Add a test function in Makefile:**

```makefile
test-cr-workflow:
	@echo "Testing Change Request workflow..."
	@curl -s -X POST http://localhost:5151/cr/new \
		-H "Content-Type: application/json" \
		-d '{"title":"Test CR","description":"Test change"}' \
		| python -m json.tool
```

**2. Call it from test-all:**

```makefile
test-all: test-new-doc test-lifecycle test-cr-workflow
	@echo "✓ All tests complete"
```

---

## How Versioning Works

### Revision Numbering Convention

**Draft/Review stages:** Use letters (RevA, RevB, RevC...)
- RevA = first draft
- RevB = after first round of changes
- RevC = after second round
- Skip I, O, Q, S, X, Z (per ASME Y14.35)

**Approved/Effective stages:** Use numbers (Rev1, Rev2, Rev3...)
- Rev1 = first approved version
- Rev2 = second approved version (triggered by a Change Request)

### Lifecycle State Machine

```
DRAFT RevA
   ↓ (submit for review)
IN_REVIEW RevA
   ↓ (all reviewers approve)
APPROVED_PENDING RevA
   ↓ (make effective)
EFFECTIVE Rev1
   ↓ (create CR to update)
DRAFT RevA (new document linked to CR)
   ↓ (review + approve)
APPROVED_PENDING RevA
   ↓ (CR approved, make effective)
EFFECTIVE Rev2
   └─ OBSOLETE Rev1 (old version archived)
```

### File Movement During Lifecycle

**When promoted from DRAFT → IN_REVIEW:**
- File moves from `02_SOPs/Draft/` to `02_SOPs/InReview/`
- Filename changes from `_DRAFT.docx` to `_IN_REVIEW.docx`
- Register updated with new file_path

**When made EFFECTIVE:**
- File moves to `02_SOPs/Effective/`
- Filename changes to `_EFFECTIVE.docx`
- Revision changes from RevA to Rev1
- Previous Rev1 moves to `_ARCHIVE/`

### Semantic Versioning for the Repository

The repository itself follows **Semantic Versioning** (semver):

**Format:** `MAJOR.MINOR.PATCH`

**Examples:**
- `1.4.0` — Current version (major release)
- `1.4.1` — Small bug fix
- `1.5.0` — New feature added
- `2.0.0` — Breaking change (API endpoints changed)

**CHANGELOG.md tracks:**
- What changed in each version
- When it was released
- What's added, changed, fixed, deprecated

**How to bump version:**

1. Make your changes
2. Update `CHANGELOG.md` with new version heading
3. Tag the commit:
   ```bash
   git tag -a v1.5.0 -m "Version 1.5.0: Added digital signature support"
   git push origin v1.5.0
   ```

---

## How To Iteratively Improve

### The Continuous Improvement Cycle

```
1. IDENTIFY NEED
   ↓
2. DESIGN SOLUTION
   ↓
3. IMPLEMENT IN CODESPACES
   ↓
4. TEST WITH make test-all
   ↓
5. COMMIT & PUSH
   ↓
6. DEPLOY TO CLIENT
   ↓
7. GATHER FEEDBACK
   ↓
(back to 1)
```

### Practical Examples

#### Example 1: Add Digital Signature Support

**1. Identify Need**
- Client asked: "Can approvers sign with a digital certificate?"

**2. Design Solution**
- Research Python libraries (cryptography, pyhanko)
- Design API endpoint: `POST /documents/ID/sign`
- Design storage: add `signature_data` field to register

**3. Implement**
```bash
make dev    # Start server
# Edit server/dms_server.py
# Add signature endpoint
# Save file → auto-reload
```

**4. Test**
```bash
make test-sign    # New test you write
```

**5. Commit**
```bash
git commit -m "Add digital signature support for approvals"
```

**6. Deploy**
- Client pulls latest code: `git pull`
- Restart their server

**7. Feedback**
- Client: "Works great, but can we store the certificate thumbprint too?"
- Iterate back to step 1

#### Example 2: Add Email Notifications

**Current state:** Notifications go to `notifications.json`, not actually sent.

**Improvement:**

**1. Choose email method** (SMTP, Microsoft Graph, SendGrid)

**2. Add configuration** to `dms_config.json`:
```json
{
  "email_enabled": true,
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "smtp_user": "notifications@acmemedical.com",
  "smtp_password": "[encrypted]"
}
```

**3. Update `routing_engine.py`:**
```python
def _dispatch_notification(self, notif):
    """Send notification via email."""
    if not self._email_enabled():
        return  # Skip if email not configured
    
    import smtplib
    from email.mime.text import MIMEText
    
    msg = MIMEText(notif["body"])
    msg["Subject"] = notif["subject"]
    msg["From"] = self.config["smtp_user"]
    msg["To"] = notif["recipient_email"]
    
    with smtplib.SMTP(self.config["smtp_server"], self.config["smtp_port"]) as server:
        server.starttls()
        server.login(self.config["smtp_user"], self.config["smtp_password"])
        server.send_message(msg)
    
    notif["notification_sent"] = True
    notif["notification_method"] = "SMTP"
```

**4. Test with a real email:**
```bash
make test-email-notification
```

**5. Document in CHANGELOG.md:**
```markdown
## [1.5.0] - 2026-05-15

### Added
- Email notification support via SMTP
- Configuration options for email server
- Fallback to JSON queue if email fails
```

### Where New Features Go

| Feature Type | File Location | Notes |
|-------------|---------------|-------|
| New API endpoint | `server/dms_server.py` | Add route like `@app.route("/new-endpoint")` |
| Routing logic | `server/routing_engine.py` | Review/approval workflows |
| CR logic | `server/cr_engine.py` | Change request lifecycle |
| CLI command | `_SCRIPTS/dms.py` | Add subparser for new command |
| Makefile shortcut | `Makefile` | Add target for common tasks |
| Word ribbon button | `ribbon/QMS_WordRibbon_v1_4_COMPLETE.bas` | Add VBA Sub |
| Word ribbon XML | `ribbon/customUI14_fixed.xml` | Add `<button>` in `<group>` |
| Excel tool | `ribbon/QMS_ExcelRibbon.bas` | Risk register functions |
| User documentation | `docs/QMS_DMS_User_Guide_*.docx` | Screenshots + instructions |

---

## Where Documentation Goes

### Documentation Hierarchy

**1. Code-Level Documentation (For Developers)**

**Docstrings in Python:**
```python
def submit_for_review(self, doc_id, doc_title, doc_version, reviewers):
    """
    Route a document to one or more reviewers.
    
    Args:
        doc_id (str): Document ID like "SOP-001"
        doc_title (str): Human-readable title
        doc_version (str): Current version like "A" or "1"
        reviewers (list): List of dicts with name/email/doc_types
    
    Returns:
        None (updates review_queue.json and notifications.json)
    
    Side effects:
        - Appends to review_queue.json
        - Sends notifications to each reviewer
        - Logs SUBMITTED_FOR_REVIEW action
    """
```

**Comments for complex logic:**
```python
# ISO 14971 risk matrix: Severity (1-5) × Probability (1-5) → RPN
# LOW: 1-3, MEDIUM: 4-8, HIGH: 9-15, CRITICAL: 16-25
rpn = severity * probability
```

**2. Architecture Documentation (For Team)**

**README.md** — System overview
- What it is, what it does
- Architecture diagram
- API endpoints
- Standards compliance
- Deployment notes

**DEV_GUIDE.md** — Daily workflow
- How to start server
- How to test
- Common tasks
- Troubleshooting

**ONBOARDING.md** (this file) — Complete explanation
- For new developers
- Step-by-step everything

**3. User Documentation (For End Users)**

**docs/QMS_DMS_User_Guide_v1_3.docx**
- How to use the desktop app
- How to use Word ribbon buttons
- Screenshots and walkthroughs

**docs/QMS_Document_Control_Reference_Guide.docx**
- Naming conventions
- Revision numbering rules
- Folder structure
- Part numbering

**4. Change Documentation (For Version History)**

**CHANGELOG.md** — What changed in each version
- Added features
- Changed behavior
- Fixed bugs
- Deprecated/removed features

**Git commit messages** — Why code changed
```bash
git commit -m "Fix: Prevent duplicate doc IDs when multiple users create docs simultaneously"
```

### When To Update What

| You did this... | Update this... |
|----------------|---------------|
| Added API endpoint | README.md (API section) + code docstring |
| Changed workflow | DEV_GUIDE.md |
| Added feature | CHANGELOG.md |
| Released version | CHANGELOG.md + git tag |
| Fixed bug | Git commit message + CHANGELOG.md |
| Added Makefile command | Makefile comment + DEV_GUIDE.md |
| Changed UI | docs/QMS_DMS_User_Guide_*.docx |
| Changed document numbering | docs/QMS_Document_Control_Reference_Guide.docx |

---

## How Everything Functions Together

### Request Flow Example: "Create a New SOP"

**User Action:** User opens desktop app, clicks "Create New Document", selects "SOP", types title "Incoming Inspection", clicks OK.

**Behind the Scenes:**

```
1. Desktop App (qms_app.py)
   ↓
   Sends HTTP POST to http://localhost:5151/documents/new
   Body: {"doc_type": "SOP", "title": "Incoming Inspection", "owner": "Jane Smith"}

2. Flask Server (dms_server.py)
   ↓
   @app.route("/documents/new") receives the request
   ↓
   Calls load_register() → reads document_register.csv
   ↓
   Calls next_doc_id("SOP") → finds last SOP-XXX, returns SOP-003
   ↓
   Creates row: {
       "doc_id": "SOP-003",
       "title": "Incoming Inspection",
       "type": "SOP",
       "version": "A",
       "status": "DRAFT",
       "owner": "Jane Smith",
       "created_date": "2026-05-07",
       ...
   }
   ↓
   Calls save_register(rows) → writes updated CSV
   ↓
   Calls log_action("DOC_CREATED", "SOP-003", "Jane Smith") → appends to audit_log.json
   ↓
   Calls _generate_docx() → creates Word file from template
   ↓
   Saves to: TEST_QMS/02_SOPs/Draft/SOP-003_RevA_Incoming_Inspection_DRAFT.docx
   ↓
   Returns JSON: {"ok": true, "doc": {...}}

3. Desktop App
   ↓
   Receives response
   ↓
   Shows success message: "Created SOP-003"
   ↓
   Refreshes document list → calls GET /documents
   ↓
   Shows SOP-003 in the DRAFT section
```

### Data Flow Example: "Route Document for Review"

**User Action:** User right-clicks SOP-003, selects "Route for Review", picks Tech Reviewer from list, clicks Submit.

```
1. Desktop App
   ↓
   POST /routing/submit-review
   Body: {
       "doc_id": "SOP-003",
       "reviewers": [{"name": "Tech Reviewer", "email": "tech@acme.com"}]
   }

2. Flask Server (dms_server.py)
   ↓
   Endpoint calls router.submit_for_review(...)
   ↓
   
3. Routing Engine (routing_engine.py)
   ↓
   Loads review_queue.json
   ↓
   Creates routing record: {
       "route_id": "RT-20260507-001",
       "doc_id": "SOP-003",
       "route_type": "REVIEW",
       "status": "PENDING",
       "reviewers": [{"name": "Tech Reviewer", ...}]
   }
   ↓
   Appends to review_queue.json
   ↓
   Loads notifications.json
   ↓
   Creates notification: {
       "notification_id": "N-...",
       "recipient_name": "Tech Reviewer",
       "recipient_email": "tech@acme.com",
       "notification_type": "REVIEW_REQUEST",
       "subject": "Review Request: SOP-003 Incoming Inspection",
       "body": "Jane Smith has submitted SOP-003 for your review...",
       "dismissed": false
   }
   ↓
   Appends to notifications.json
   ↓
   Calls _dispatch_notification() → (currently a stub, would send email)
   ↓
   Saves review_queue.json and notifications.json

4. Flask Server
   ↓
   Updates document_register.csv:
       status: DRAFT → IN_REVIEW
       file_path: moves file from Draft/ to InReview/
   ↓
   Logs audit event: SUBMITTED_FOR_REVIEW
   ↓
   Returns {"ok": true}

5. Desktop App
   ↓
   Shows "Document routed to Tech Reviewer"
   ↓
   Refreshes list → SOP-003 now shows IN_REVIEW status
```

### The Register as Single Source of Truth

**Everything is driven by `document_register.csv`:**

- Desktop app displays documents? Read the register.
- Word ribbon shows doc status? Call `/documents/<id>` → reads register.
- Report overdue reviews? Query register for next_review_date < today.
- Audit trail? audit_log.json tracks changes to register.

**Why CSV and not a database?**

1. **Simplicity** — No PostgreSQL to install, no migrations
2. **Portability** — Works on network drives, Google Drive, OneDrive
3. **Human-readable** — Open in Excel, audit it directly
4. **Backup-friendly** — Just copy the folder
5. **Client isolation** — Each client has their own QMS Root folder

**Tradeoff:** Not suitable for hundreds of concurrent users. Perfect for 5-50 person companies.

---

## Real-World Deployment

### How This Gets Used by Clients

**Scenario:** You're a consultant. You sell QMS setup to a medical device startup.

**What You Deliver:**

1. **The Code** (this repository)
   - They get a private fork or copy
   - They own it, can modify it

2. **QMS Root Folder Structure**
   - You create it on their network drive: `Z:\QMS\`
   - Or on their Google Drive: `G:\Shared drives\QMS\`
   - Populate with `_REGISTER/`, folder structure, empty CSV

3. **Configuration File** (`dms_config.json`)
   - Set their QMS Root path
   - Set their company name, code
   - Set their project list
   - Define their folder labels

4. **Installation on Each User's Machine**
   - Run `installer/install_v1_3c.bat`
   - Installs Python, Flask, dependencies
   - Installs desktop app shortcut
   - Injects Word/Excel ribbons

5. **Team Roster Setup**
   - Add their employees to `team_roster.json`
   - Define roles (QA Lead, Approver, Reviewer, etc.)

6. **Training**
   - Walk them through creating first document
   - Show routing workflow
   - Show change request process

### Multi-Client Deployment Model

**Each client is completely isolated:**

```
Client A
├─ QMS Root: Z:\ClientA_QMS\
├─ Server: runs on ClientA's network
├─ Config: points to Z:\ClientA_QMS\
└─ Data: stays on their infrastructure

Client B
├─ QMS Root: \\ClientB-Server\QMS\
├─ Server: runs on ClientB's network
├─ Config: points to \\ClientB-Server\QMS\
└─ Data: stays on their infrastructure

You (Consultant)
├─ GitHub Repo: bgrdjt/QMS (code only)
├─ Codespaces: for developing improvements
└─ Rollout: git pull on each client to update
```

**Updating All Clients:**

1. You develop a feature in Codespaces
2. Commit and push to main
3. Each client runs: `git pull`
4. They restart their server
5. Everyone gets the new feature

### Hosting Options for the Server

**Option 1: Each user runs server locally**
- User starts `python dms_server.py` on their laptop
- Server runs on `localhost:5151`
- QMS Root on network drive (Z:\QMS\)
- Pros: Simple, no central server needed
- Cons: Server must be running for Word ribbon to work

**Option 2: One user runs server for whole team**
- One machine runs server 24/7
- Other users connect to that machine's IP: `http://192.168.1.50:5151`
- QMS Root on network drive (accessible by server machine)
- Pros: Always available
- Cons: Single point of failure

**Option 3: Linux server in office**
- Dedicated Ubuntu server or Raspberry Pi
- Runs server as systemd service
- DNS name: `http://qms.company.local:5151`
- QMS Root on NAS (Synology, QNAP, etc.)
- Pros: Reliable, always-on
- Cons: Requires IT setup

**Option 4: Cloud-hosted (advanced)**
- AWS EC2, Azure VM, Google Cloud
- QMS Root on cloud storage (S3, Azure Blob)
- Accessible from anywhere
- Pros: Remote work friendly
- Cons: Network latency, costs

---

## Common Scenarios

### Scenario 1: "I Need to Add a New Document Type"

**Current types:** SOP, WI, FM, RM, DC, etc.

**Add a new one: "Training Material" (TM)**

**Step 1: Update prefix scheme**

Edit `server/dms_config.json`:
```json
"prefix_scheme": {
    "SOP": "Standard Operating Procedure",
    "TM": "Training Material",   ← Add this
    ...
}
```

**Step 2: Create folder**

In QMS Root:
```bash
mkdir -p TEST_QMS/12_TRAINING_MATERIALS/{Draft,InReview,Effective,Obsolete}
```

**Step 3: Update active folders**

Edit `dms_config.json`:
```json
"active_folders": [
    "01_QUALITY_MANUAL",
    "02_SOPs",
    ...
    "12_TRAINING_MATERIALS"   ← Add this
]
```

**Step 4: Test**

```bash
curl -X POST http://localhost:5151/documents/new \
  -d '{"doc_type":"TM","title":"GMP Training"}'
```

Should create `TM-001`.

---

### Scenario 2: "I Need to Add a Custom Role"

**Step 1: Add role via API**

```bash
curl -X POST http://localhost:5151/roles/add \
  -H "Content-Type: application/json" \
  -d '{"role": "Regulatory Affairs"}'
```

**Step 2: Assign to team member**

```bash
curl -X POST http://localhost:5151/roster/update \
  -d '{
    "member_id": "M003",
    "updates": {"roles": ["Developer", "Regulatory Affairs"]},
    "changed_by": "QA Lead",
    "reason": "Assigned RA responsibilities"
  }'
```

**Step 3: Use in routing**

When routing a document, specify `doc_types: ["TM"]` for that role.

---

### Scenario 3: "I Want to See All Documents Expiring in 30 Days"

**Option 1: Use existing endpoint**

```bash
curl "http://localhost:5151/review-due?days=30"
```

**Option 2: Add a Makefile command**

Edit `Makefile`:
```makefile
review-due-30:
	@curl -s "http://localhost:5151/review-due?days=30" | python -m json.tool
```

Now just: `make review-due-30`

---

## Troubleshooting

### "Server won't start"

**Error:** `Address already in use`

**Solution:**
```bash
pkill -f dms_server
make dev
```

---

### "Port 5151 not forwarded in Codespaces"

**Solution:**
1. Click Ports tab (bottom panel)
2. Look for port 5151
3. Right-click → Port Visibility → Public
4. Click the globe icon to open

---

### "TEST_QMS folder is corrupted"

**Solution:**
```bash
make reset    # Wipes and recreates from scratch
```

---

### "Import error: No module named flask"

**Solution:**
```bash
make setup    # Reinstalls all dependencies
```

---

### "Document register CSV is locked"

**Cause:** Someone has it open in Excel

**Solution:**
- Close Excel
- Or implement file locking in Python (future improvement)

---

### "Auto-reload isn't working"

**Check:** Is `debug=True` and `use_reloader=True` in `dms_server.py`?

```python
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5151, debug=True, use_reloader=True)
```

---

## Summary: Your Mental Model

**Think of this system as:**

1. **A backend API** (Flask) that manages documents
2. **A file-based database** (CSV/JSON in QMS Root folder)
3. **Multiple frontends** (desktop app, Word ribbon, Excel ribbon)
4. **A development environment** (Codespaces with auto-reload)
5. **A deployment model** (each client isolated with their own QMS Root)

**The flow:**
```
Developer (you)
   ↓ codes in Codespaces
   ↓ tests with make commands
   ↓ commits to GitHub
   
Clients
   ↓ git pull to get updates
   ↓ run installation script
   ↓ point to their QMS Root folder
   
End Users
   ↓ use desktop app or Word ribbon
   ↓ API calls go to Flask server
   ↓ data saved to QMS Root folder
   ↓ audit trail tracks everything
```

**Key Commands:**
```bash
make setup      # First time: install dependencies
make env        # Create test environment
make dev        # Start server (auto-reload)
make test-all   # Run all tests
make reset      # Wipe and start fresh
git commit      # Save your work
git push        # Share with team/clients
```

**Key Files:**
- `server/dms_server.py` — All API endpoints
- `server/routing_engine.py` — Review/approval logic
- `server/cr_engine.py` — Change request logic
- `Makefile` — Quick commands
- `CHANGELOG.md` — Version history
- `README.md` — Architecture reference
- `DEV_GUIDE.md` — Daily workflow
- `ONBOARDING.md` — This guide

---

## Next Steps

**1. Experiment**
```bash
make dev
make test-all
```

**2. Read the code**
- Start with `server/dms_server.py`
- Follow one endpoint from route to register update

**3. Make a small change**
- Add a comment to a function
- Save and watch auto-reload

**4. Add a feature**
- Pick something from the roadmap in README.md
- Implement, test, commit

**5. Share**
```bash
git push
```

---

**Welcome to the QMS development team!** You now understand the entire system from Codespaces to client deployment. Start coding, and refer back to this guide whenever you need a refresher.

Questions? See [README.md](README.md) for architecture details or [DEV_GUIDE.md](DEV_GUIDE.md) for daily commands.
