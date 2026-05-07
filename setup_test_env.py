#!/usr/bin/env python3
"""
Test environment setup script for Codespaces development.
Creates TEST_QMS folder with sample documents, team roster, and audit log.
"""

import csv
import datetime
import json
import os
import shutil
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────

TEST_ROOT = Path("/workspaces/QMS/TEST_QMS")
CONFIG_PATH = Path("/workspaces/QMS/server/dms_config.json")

COMPANY_NAME = "Acme Medical Devices"
COMPANY_CODE = "ACM"
CURRENT_USER = "Dev User"
CURRENT_EMAIL = "dev@acmemedical.com"

# ── Folder structure ──────────────────────────────────────────────────────────

QMS_FOLDERS = [
    "01_QUALITY_MANUAL",
    "02_SOPs",
    "03_WORK_INSTRUCTIONS",
    "04_FORMS_TEMPLATES",
    "05_RISK_MANAGEMENT",
    "06_DESIGN_CONTROL",
    "07_SUPPLIER_MANAGEMENT",
    "08_PURCHASING_OUTSOURCING",
    "09_AUDIT_RECORDS",
    "10_TRAINING_RECORDS",
    "11_CHANGE_REQUESTS",
    "INFORMAL_DOCS",
    "PRODUCTS",
    "_REGISTER",
    "_ARCHIVE",
]

SUBFOLDERS = ["Draft", "InReview", "ApprovedPending", "Effective", "Obsolete"]

# ── Sample documents ──────────────────────────────────────────────────────────

SAMPLE_DOCS = [
    {
        "doc_id": "QM-001",
        "title": "Quality Manual",
        "type": "Quality Manual",
        "version": "1",
        "status": "EFFECTIVE",
        "doc_category": "FORMAL",
        "owner": "QA Lead",
        "created_date": "2025-01-15",
        "last_modified": "2025-01-15",
        "effective_date": "2025-01-20",
        "next_review_date": "2026-01-20",
        "approved_by": "QA Lead",
        "folder": "01_QUALITY_MANUAL/Effective",
        "file_name": "QM-001_Rev1_Quality_Manual_EFFECTIVE.docx",
        "notes": "ISO 13485:2016 compliant quality manual",
    },
    {
        "doc_id": "SOP-001",
        "title": "Document Control Procedure",
        "type": "SOP",
        "version": "2",
        "status": "EFFECTIVE",
        "doc_category": "FORMAL",
        "owner": "QA Lead",
        "created_date": "2024-06-10",
        "last_modified": "2025-02-01",
        "effective_date": "2025-02-05",
        "next_review_date": "2026-02-05",
        "approved_by": "QA Lead",
        "folder": "02_SOPs/Effective",
        "file_name": "SOP-001_Rev2_Document_Control_Procedure_EFFECTIVE.docx",
        "notes": "Core document control process per ISO 13485 §4.2",
    },
    {
        "doc_id": "SOP-002",
        "title": "Incoming Inspection",
        "type": "SOP",
        "version": "A",
        "status": "DRAFT",
        "doc_category": "FORMAL",
        "owner": "Tech Reviewer",
        "created_date": "2026-05-01",
        "last_modified": "2026-05-07",
        "folder": "02_SOPs/Draft",
        "file_name": "SOP-002_RevA_Incoming_Inspection_DRAFT.docx",
        "notes": "New procedure under development",
    },
    {
        "doc_id": "SOP-003",
        "title": "Risk Management Process",
        "type": "SOP",
        "version": "B",
        "status": "IN_REVIEW",
        "doc_category": "FORMAL",
        "owner": "QA Lead",
        "created_date": "2026-04-15",
        "last_modified": "2026-05-05",
        "folder": "02_SOPs/InReview",
        "file_name": "SOP-003_RevB_Risk_Management_Process_IN_REVIEW.docx",
        "notes": "Submitted for technical review",
    },
    {
        "doc_id": "PRJ-001-DC-001",
        "title": "Design Requirements Specification",
        "type": "Design Control",
        "version": "A",
        "status": "DRAFT",
        "doc_category": "FORMAL",
        "owner": "Dev User",
        "created_date": "2026-05-03",
        "last_modified": "2026-05-06",
        "folder": "PRODUCTS/PRJ-001_Cardiac_Monitor/06_DESIGN_CONTROL/Draft",
        "file_name": "PRJ-001-DC-001_RevA_Design_Requirements_Specification_DRAFT.docx",
        "notes": "Project-scoped design document",
    },
    {
        "doc_id": "FS-001",
        "title": "Feasibility Study - Cardiac Monitor",
        "type": "Feasibility Study",
        "version": "1",
        "status": "APPROVED",
        "doc_category": "INFORMAL",
        "owner": "Tech Reviewer",
        "created_date": "2025-11-10",
        "last_modified": "2025-11-20",
        "folder": "INFORMAL_DOCS",
        "file_name": "FS-001_Rev1_Feasibility_Study_Cardiac_Monitor_APPROVED.docx",
        "notes": "NOT UNDER QMS",
    },
    {
        "doc_id": "CR-0001",
        "title": "CR Form — Update Document Control SOP",
        "type": "Change Request",
        "version": "A",
        "status": "DRAFT",
        "doc_category": "FORMAL",
        "owner": "QA Lead",
        "created_date": "2026-02-01",
        "last_modified": "2026-02-01",
        "cr_id": "CR-0001",
        "folder": "11_CHANGE_REQUESTS/Draft",
        "file_name": "CR-0001_RevA_CR_Form_Update_Document_Control_SOP_DRAFT.docx",
        "notes": "CR Form for SOP-001 Rev2",
    },
]

# ── Sample team roster ────────────────────────────────────────────────────────

SAMPLE_ROSTER = {
    "members": [
        {
            "member_id": "M001",
            "name": "QA Lead",
            "email": "qa.lead@acmemedical.com",
            "roles": ["QA Lead", "Management Rep", "Approver"],
            "doc_types": ["SOP", "Quality Manual", "Change Request"],
            "active": True,
            "role_history": [
                {
                    "timestamp": "2024-01-15T00:00:00Z",
                    "action": "ROLE_ASSIGNED",
                    "roles": ["QA Lead", "Management Rep", "Approver"],
                    "changed_by": "System",
                    "reason": "Initial setup",
                }
            ],
        },
        {
            "member_id": "M002",
            "name": "Tech Reviewer",
            "email": "tech@acmemedical.com",
            "roles": ["Technical Reviewer", "Design Engineer"],
            "doc_types": ["SOP", "Design Control", "Risk Management"],
            "active": True,
            "role_history": [
                {
                    "timestamp": "2024-01-15T00:00:00Z",
                    "action": "ROLE_ASSIGNED",
                    "roles": ["Technical Reviewer"],
                    "changed_by": "System",
                    "reason": "Initial setup",
                },
                {
                    "timestamp": "2025-06-01T00:00:00Z",
                    "action": "ROLE_CHANGED",
                    "roles": ["Technical Reviewer", "Design Engineer"],
                    "changed_by": "QA Lead",
                    "reason": "Promotion to Design Engineer",
                },
            ],
        },
        {
            "member_id": "M003",
            "name": "Dev User",
            "email": "dev@acmemedical.com",
            "roles": ["Developer", "Document Author"],
            "doc_types": ["Design Control", "SOP"],
            "active": True,
            "role_history": [
                {
                    "timestamp": "2026-05-01T00:00:00Z",
                    "action": "ROLE_ASSIGNED",
                    "roles": ["Developer", "Document Author"],
                    "changed_by": "QA Lead",
                    "reason": "New hire",
                }
            ],
        },
    ],
    "custom_roles": [
        "QA Lead",
        "Management Rep",
        "Approver",
        "Technical Reviewer",
        "Design Engineer",
        "Developer",
        "Document Author",
        "Manufacturing",
        "Purchasing",
    ],
}

# ── Sample audit log ──────────────────────────────────────────────────────────

SAMPLE_AUDIT_LOG = [
    {
        "timestamp": "2025-01-15T10:30:00Z",
        "action": "DOC_CREATED",
        "doc_id": "QM-001",
        "user": "QA Lead",
        "details": "Quality Manual",
    },
    {
        "timestamp": "2025-01-20T14:00:00Z",
        "action": "MADE_EFFECTIVE",
        "doc_id": "QM-001",
        "user": "QA Lead",
        "details": "Rev1 | Effective:2025-01-20",
    },
    {
        "timestamp": "2024-06-10T09:15:00Z",
        "action": "DOC_CREATED",
        "doc_id": "SOP-001",
        "user": "QA Lead",
        "details": "Document Control Procedure",
    },
    {
        "timestamp": "2025-02-01T16:45:00Z",
        "action": "CR_CREATED",
        "doc_id": "CR-0001",
        "user": "QA Lead",
        "details": "Update Document Control SOP",
    },
    {
        "timestamp": "2025-02-05T11:00:00Z",
        "action": "MADE_EFFECTIVE",
        "doc_id": "SOP-001",
        "user": "QA Lead",
        "details": "CR:CR-0001 | Rev2",
    },
    {
        "timestamp": "2026-05-01T08:00:00Z",
        "action": "DOC_CREATED",
        "doc_id": "SOP-002",
        "user": "Tech Reviewer",
        "details": "Incoming Inspection",
    },
    {
        "timestamp": "2026-04-15T13:20:00Z",
        "action": "DOC_CREATED",
        "doc_id": "SOP-003",
        "user": "QA Lead",
        "details": "Risk Management Process",
    },
    {
        "timestamp": "2026-05-05T10:30:00Z",
        "action": "SUBMITTED_FOR_REVIEW",
        "doc_id": "SOP-003",
        "user": "QA Lead",
        "details": "Routed to Tech Reviewer",
    },
]

# ── Sample projects ───────────────────────────────────────────────────────────

SAMPLE_PROJECTS = {
    "PRJ-001": "Cardiac Monitor",
    "PRJ-002": "Infusion Pump",
}

# ── Helper functions ──────────────────────────────────────────────────────────


def create_folder_structure():
    """Create QMS folder structure with subfolders."""
    print(f"Creating folder structure at {TEST_ROOT}...")
    for folder in QMS_FOLDERS:
        folder_path = TEST_ROOT / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        # Create lifecycle subfolders for main QMS folders (01-11)
        if folder.split("_")[0].isdigit() or folder == "INFORMAL_DOCS":
            for subfolder in SUBFOLDERS:
                (folder_path / subfolder).mkdir(exist_ok=True)

    # Create project-specific structure
    for proj_id, proj_name in SAMPLE_PROJECTS.items():
        proj_path = TEST_ROOT / "PRODUCTS" / f"{proj_id}_{proj_name.replace(' ', '_')}"
        for folder in [
            "05_RISK_MANAGEMENT",
            "06_DESIGN_CONTROL",
            "07_SUPPLIER_MANAGEMENT",
        ]:
            folder_path = proj_path / folder
            for subfolder in SUBFOLDERS:
                (folder_path / subfolder).mkdir(parents=True, exist_ok=True)

    print("✓ Folder structure created")


def create_document_register():
    """Create document register CSV with sample documents."""
    print("Creating document register...")
    register_path = TEST_ROOT / "_REGISTER" / "document_register.csv"

    fieldnames = [
        "doc_id",
        "title",
        "type",
        "version",
        "status",
        "doc_category",
        "owner",
        "created_date",
        "last_modified",
        "effective_date",
        "next_review_date",
        "approved_by",
        "cr_id",
        "file_path",
        "pdf_path",
        "notes",
        "iso_clauses",
        "risk_refs",
        "keywords",
    ]

    with open(register_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for doc in SAMPLE_DOCS:
            row = {field: doc.get(field, "") for field in fieldnames}
            row["file_path"] = f"{doc['folder']}/{doc['file_name']}"
            writer.writerow(row)

    print(f"✓ Document register created with {len(SAMPLE_DOCS)} documents")


def create_team_roster():
    """Create team roster JSON."""
    print("Creating team roster...")
    roster_path = TEST_ROOT / "_REGISTER" / "team_roster.json"
    roster_path.write_text(json.dumps(SAMPLE_ROSTER, indent=2), encoding="utf-8")
    print(f"✓ Team roster created with {len(SAMPLE_ROSTER['members'])} members")


def create_audit_log():
    """Create audit log JSON."""
    print("Creating audit log...")
    log_path = TEST_ROOT / "_REGISTER" / "audit_log.json"
    log_path.write_text(json.dumps(SAMPLE_AUDIT_LOG, indent=2), encoding="utf-8")
    print(f"✓ Audit log created with {len(SAMPLE_AUDIT_LOG)} events")


def create_other_files():
    """Create other required JSON files."""
    print("Creating supporting files...")

    # Notifications
    (TEST_ROOT / "_REGISTER" / "notifications.json").write_text("[]", encoding="utf-8")

    # Review queue
    (TEST_ROOT / "_REGISTER" / "review_queue.json").write_text("[]", encoding="utf-8")

    # Change requests
    cr_data = [
        {
            "cr_id": "CR-0001",
            "title": "Update Document Control SOP",
            "description": "Add digital signature workflow to document control procedure",
            "reason": "Regulatory requirement for FDA submission",
            "change_type": "Process Change",
            "initiator": "QA Lead",
            "initiator_email": "qa.lead@acmemedical.com",
            "linked_doc_ids": "SOP-001",
            "risk_ref": "",
            "impact_analysis": "Affects document approval workflow",
            "training_required": "YES",
            "training_notes": "All approvers must complete digital signature training",
            "target_effective_date": "2025-02-05",
            "effective_date": "",
            "status": "DRAFT",
            "created_date": "2026-02-01",
            "last_modified": "2026-02-01",
            "approved_by": "",
            "closed_by": "",
            "post_impl_notes": "",
            "cancel_reason": "",
            "cr_form_doc_id": "CR-0001",
        }
    ]
    (TEST_ROOT / "_REGISTER" / "change_requests.json").write_text(
        json.dumps(cr_data, indent=2), encoding="utf-8"
    )

    # Change requests log
    (TEST_ROOT / "_REGISTER" / "change_requests_log.json").write_text(
        "[]", encoding="utf-8"
    )

    print("✓ Supporting files created")


def create_config():
    """Create dms_config.json pointing to TEST_QMS."""
    print("Creating server configuration...")

    config = {
        "qms_root": str(TEST_ROOT),
        "current_user": CURRENT_USER,
        "current_email": CURRENT_EMAIL,
        "company_name": COMPANY_NAME,
        "company_code": COMPANY_CODE,
        "client_name": "Development Environment",
        "projects": SAMPLE_PROJECTS,
        "project_prefix_style": "prefix",
        "number_padding": 3,
        "header_color": "003F7F",
        "cr_color": "8B1A00",
        "doc_font": "Arial",
        "doc_font_size": 11,
        "logo_path": "",
        "active_folders": [
            "01_QUALITY_MANUAL",
            "02_SOPs",
            "03_WORK_INSTRUCTIONS",
            "04_FORMS_TEMPLATES",
            "05_RISK_MANAGEMENT",
            "06_DESIGN_CONTROL",
            "07_SUPPLIER_MANAGEMENT",
            "08_PURCHASING_OUTSOURCING",
            "09_AUDIT_RECORDS",
            "10_TRAINING_RECORDS",
            "11_CHANGE_REQUESTS",
        ],
        "folder_labels": {
            "01_QUALITY_MANUAL": "01_QUALITY_MANUAL",
            "02_SOPs": "02_SOPs",
            "03_WORK_INSTRUCTIONS": "03_WORK_INSTRUCTIONS",
            "04_FORMS_TEMPLATES": "04_FORMS_TEMPLATES",
            "05_RISK_MANAGEMENT": "05_RISK_MANAGEMENT",
            "06_DESIGN_CONTROL": "06_DESIGN_CONTROL",
            "07_SUPPLIER_MANAGEMENT": "07_SUPPLIER_MANAGEMENT",
            "08_PURCHASING_OUTSOURCING": "08_PURCHASING_OUTSOURCING",
            "09_AUDIT_RECORDS": "09_AUDIT_RECORDS",
            "10_TRAINING_RECORDS": "10_TRAINING_RECORDS",
            "11_CHANGE_REQUESTS": "11_CHANGE_REQUESTS",
        },
        "prefix_scheme": {
            "QM": "Quality Manual",
            "SOP": "Standard Operating Procedure",
            "WI": "Work Instruction",
            "FM": "Form",
            "TM": "Template",
            "RM": "Risk Management",
            "DC": "Design Control",
            "SM": "Supplier Management",
            "PO": "Purchase Order",
            "AR": "Audit Record",
            "TR": "Training Record",
            "CR": "Change Request",
        },
        "informal_prefix_scheme": {
            "FS": "Feasibility Study",
            "BD": "Business Development",
            "MM": "Meeting Minutes",
            "PP": "Project Plan",
        },
        "informal_folder": "INFORMAL_DOCS",
    }

    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"✓ Configuration saved to {CONFIG_PATH}")


def main():
    """Set up complete test environment."""
    print("\n" + "=" * 70)
    print("QMS Test Environment Setup")
    print("=" * 70 + "\n")

    if TEST_ROOT.exists():
        response = input(
            f"{TEST_ROOT} already exists. Delete and recreate? (y/N): "
        ).lower()
        if response == "y":
            shutil.rmtree(TEST_ROOT)
            print(f"✓ Removed existing {TEST_ROOT}")
        else:
            print("Aborted.")
            return

    create_folder_structure()
    create_document_register()
    create_team_roster()
    create_audit_log()
    create_other_files()
    create_config()

    print("\n" + "=" * 70)
    print("✓ Test environment ready!")
    print("=" * 70)
    print(f"\nQMS Root: {TEST_ROOT}")
    print(f"Config:   {CONFIG_PATH}")
    print(f"\nDocuments:     {len(SAMPLE_DOCS)}")
    print(f"Team members:  {len(SAMPLE_ROSTER['members'])}")
    print(f"Audit events:  {len(SAMPLE_AUDIT_LOG)}")
    print(f"Projects:      {len(SAMPLE_PROJECTS)}")
    print("\nRun 'make dev' to start the server with this test data.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
