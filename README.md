# QMS
Joshua is clearly the apex predator

CopyQMS Document Management System
Version 1.4 | ISO 13485:2016 · ISO 9001:2015 · ISO 14971:2019 · FDA QMSR
What This System Is
A self-contained, script-powered Quality Management System (QMS) for small medical device companies. It replicates the core functions of commercial platforms like Greenlight Guru — document control, version tracking, change request management, approval workflows, risk management structure, routing, and audit trails — without subscription fees or vendor lock-in.
The system is designed to be deployed to clients as a consultancy offering. Each client gets their own QMS Root folder (local drive, network share, or cloud sync folder). The code in this repository is shared infrastructure; client document data lives separately.

Architecture
┌─────────────────────────────────────────────────────────┐
│  LOCAL (client machine)                                  │
│                                                          │
│  qms_app.py (PyQt5 desktop GUI)                         │
│  Word Ribbon (VBA + customUI14.xml)                     │
│  Excel Ribbon (VBA + customUI_excel.xml)                │
│       │                                                  │
│       └──► localhost:5151                               │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  server/dms_server.py  (Flask REST API)                 │
│  server/routing_engine.py  (review routing)             │
│  server/cr_engine.py   (change requests)                │
│       │                                                  │
│       └──► QMS Root Folder (network/cloud)             │
│               _REGISTER/document_register.csv           │
│               _REGISTER/audit_log.json                  │
│               _REGISTER/change_requests.json            │
│               _REGISTER/review_queue.json               │
│               _REGISTER/notifications.json              │
│               _REGISTER/team_roster.json                │
│               01_QUALITY_MANUAL/ ... 11_CHANGE_REQUESTS/│
│               INFORMAL_DOCS/                            │
│               _ARCHIVE/                                 │
└─────────────────────────────────────────────────────────┘
The server is stateless — all persistent data lives in the QMS Root folder pointed to by server/dms_config.json. Multiple users can share one QMS Root on a network drive; each runs their own local server instance.

Standards Addressed
StandardScopeKey Clauses CoveredISO 13485:2016Medical device QMS§4.2 (document control), §7.1 (risk), §7.3 (design), §7.4 (purchasing), §8.2 (audit), §8.5 (CAPA)ISO 9001:2015General QMS§7.5 (documented information), §9.3 (management review), §10 (improvement)ISO 14971:2019Risk managementRisk register template, RPN calculator, clause mapping per documentFDA QMSRUS regulatory (eff. Feb 2026)Incorporates ISO 13485 by reference; DDF/MDF terminology used

Document Lifecycle
Formal (Full QMS) Documents
DRAFT → IN_REVIEW → APPROVED_PENDING → EFFECTIVE → OBSOLETE

Requires a Change Request (CR) to become EFFECTIVE
CR controls effectivity date and simultaneous release of linked documents
Prior EFFECTIVE version automatically archived to _ARCHIVE on new effectivity

Informal (Not Under QMS) Documents
DRAFT → IN_REVIEW → APPROVED

No CR required
Sign-off block included but no ISO clause mapping
Register shows "NOT UNDER QMS" in category column
Used for: feasibility studies, BD docs, meeting minutes, project plans


Key Files
FilePurposeserver/dms_server.pyFlask REST API on port 5151. All app and ribbon calls route through here.server/routing_engine.pyReview/approval routing, notification queue, team roster with role historyserver/cr_engine.pyChange Request lifecycle: create, review, approve, make-effective, closeserver/dms_config.jsonRuntime config: QMS root path, user settings, client customization (gitignored)_SCRIPTS/dms.pyCLI controller for all document operations including importribbon/QMS_WordRibbon_v1_4_COMPLETE.basWord VBA module — all 16 ribbon buttonsribbon/customUI14_fixed.xmlWord ribbon XML — 5 groups: Document, Review, Routing, Change Request, Notificationsribbon/QMS_ExcelRibbon.basExcel VBA — risk register and traceability matrix tools

API Endpoints (localhost:5151)
Core Documents

GET  /ping — health check, returns version
GET  /config — get current configuration
POST /config — update configuration
GET  /documents — list all documents (filterable by status, type, category, cr_id)
GET  /documents/<doc_id> — single document
POST /documents/new — create and scaffold new document
POST /documents/import — register existing file into DMS
POST /documents/<doc_id>/promote — advance lifecycle status
POST /documents/<doc_id>/attach-cr — link a CR to a document
POST /documents/<doc_id>/obsolete — archive document
POST /documents/<doc_id>/open — open file in OS default app

Change Requests

GET  /cr — list CRs
POST /cr/new — create CR + auto-generate CR form document
GET  /cr/<cr_id> — CR detail with linked docs
POST /cr/<cr_id>/submit-review — CR → IN_REVIEW
POST /cr/<cr_id>/approve — CR → APPROVED, linked docs → APPROVED_PENDING
POST /cr/<cr_id>/make-effective — manual trigger: all linked docs → EFFECTIVE simultaneously
POST /cr/<cr_id>/close — post-implementation review complete
POST /cr/<cr_id>/cancel
GET  /cr/pending-effective — CRs approved and awaiting effectivity trigger

Routing

GET  /routing/queue — all routing records (filterable)
POST /routing/submit-review — route document to reviewers
POST /routing/submit-approval — route to approver
POST /routing/complete-review — reviewer submits findings (pass or reject)
POST /routing/recall — author recalls submitted document

Team Roster

GET  /roster — all members
POST /roster/add — add member (supports multiple simultaneous roles)
POST /roster/update — update member (role change recorded in role_history)
GET  /roster/<member_id>/role-history — full role change audit trail
GET  /roster/<member_id>/roles-at-date?date=YYYY-MM-DD — historical role lookup

Roles

GET  /roles — client's custom role list
POST /roles/add — add a role
POST /roles/remove — remove a role
POST /roles/set — replace entire role list

Notifications

GET  /notifications — user's notification inbox
POST /notifications/dismiss — mark one read
POST /notifications/dismiss-all — clear inbox

Stats

GET  /stats — document counts by status, routing counts, CR counts, review due count
GET  /review-due?days=60 — documents approaching annual review date
GET  /audit-log — last 200 audit events


Configuration Schema (dms_config.json)
json{
  "qms_root":             "Z:\\QMS",
  "current_user":         "Jane Smith",
  "current_email":        "jane@company.com",
  "company_name":         "Acme Medical",
  "company_code":         "ACM",
  "client_name":          "",
  "projects": {
    "P001": "Cardiac Monitor",
    "P002": "Infusion Pump"
  },
  "project_prefix_style": "prefix",
  "number_padding":        3,
  "header_color":          "003F7F",
  "cr_color":              "8B1A00",
  "doc_font":              "Arial",
  "doc_font_size":         11,
  "logo_path":             "",
  "active_folders": ["01_QUALITY_MANUAL","02_SOPs",...],
  "folder_labels":  {"02_SOPs": "02_SOPs"},
  "prefix_scheme":  {"SOP": "Standard Operating Procedure",...},
  "informal_prefix_scheme": {"FS": "Feasibility Study",...},
  "informal_folder": "INFORMAL_DOCS"
}

Document Numbering
Format: {PROJECT_CODE}-{PREFIX}-{NNN} (project-level) or {PREFIX}-{NNN} (QMS-level)
Examples:

SOP-007 — QMS-level shared SOP, no project
P001-SOP-007 — SOP belonging to Project P001
CR-0001 — Change Request (4-digit padding)

Revision convention:

RevA, RevB... — draft/review stages (omit I, O, Q, S, X, Z per ASME Y14.35)
Rev1, Rev2... — approved/effective versions


Notification Dispatch (Email Stub)
Notifications are fully built and queued in _REGISTER/notifications.json. The outbound send is stubbed in routing_engine.py → _dispatch_notification(). To wire in email:
python# Option A: SMTP
from qms_email import send_email
send_email(notif["recipient_email"], notif["subject"], notif["body"])

# Option B: Microsoft Graph (M365)
from qms_graph import send_via_graph
send_via_graph(notif["recipient_email"], notif["subject"], notif["body"])

# Option C: Teams webhook
import requests
requests.post(WEBHOOK_URL, json={"text": notif["body"]})

Running in Codespaces
bash# Install dependencies (done automatically by devcontainer.json)
pip install -r requirements.txt
npm install -g docx

# Start the server
cd server
python dms_server.py
# Server runs on port 5151 (forwarded automatically by Codespaces)

# CLI usage
cd _SCRIPTS
python dms.py new SOP "Incoming Inspection" --owner "Jane Smith"
python dms.py import "old_doc.docx" --type SOP --title "Legacy Procedure" --owner "Jane Smith"
python dms.py list
python dms.py promote SOP-001 review --user "Jane Smith"
python dms.py stats

What Is Not In This Repo

qms_app.py — PyQt5 desktop GUI (cannot run in headless Codespaces; run locally)
_REGISTER/ — client document data (lives on network/cloud drive)
QMS/, PRODUCTS/, INFORMAL_DOCS/, _ARCHIVE/ — document folders
server/dms_config.json — contains client paths and credentials (gitignored)


Roadmap
PriorityItemHIGHEmail dispatch — wire SMTP or Microsoft Graph into routing_engine._dispatch_notification()HIGHFull content for seeded placeholder documentsHIGHProject-scoped DDF folder structureMEDIUMBidirectional Word↔Register sync (read CR number from document header)MEDIUMSQLite upgrade for document_register.csv (concurrent write safety)MEDIUMdms.py redline commandMEDIUMCloud path auto-detection in SettingsLOWWeb UI (Flask/React) to replace desktop appLOWDigital signature integrationLOWSharePoint list sync

Consultancy Deployment Notes
Each client gets:

A fresh QMS Root folder on their infrastructure (network share, Google Drive, OneDrive)
The package installed on each user's machine via install_v1_3c.bat
Their own dms_config.json pointing to their QMS Root
Word/Excel ribbon templates injected via Office RibbonX Editor
Their company code, project list, and folder structure configured in Settings

Client document data is completely isolated — registers, documents, and archives never mix between clients. The code in this repo is the shared platform.