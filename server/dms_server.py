#!/usr/bin/env python3
"""
QMS DMS Server v1.4
Changes:
- Hardened JSON error handling (fixes "expecting value line 1 col 1" errors)
- Client configuration: company code, custom folder names, prefix scheme, active folders
- Informal document type: NOT UNDER QMS lifecycle, separate folder tree
- Multi-role roster support via updated routing_engine
- /roster endpoints updated for multi-role and role history
- /roster/roles endpoints for custom role management
"""

import os, sys, json, csv, shutil, datetime, re, subprocess, uuid
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS

sys.path.insert(0, str(Path(__file__).parent))
from routing_engine import RoutingEngine, DEFAULT_ROLES
from cr_engine      import CREngine

app  = Flask(__name__)
CORS(app)

# ── SAFE JSON RESPONSE HELPER ─────────────────────────────────────────────────
# Root cause of "expecting value line 1 column 1 char 0":
# When QMS Root is not configured, server-side functions return None/empty
# and the Flask response body is empty. The app's requests.get().json()
# then tries to parse "" as JSON and throws the error.
# Fix: always return valid JSON, even for error conditions.

def safe_json(data, status=200):
    """Always return a valid JSON response."""
    if data is None:
        data = {"error": "No data returned"}
    return jsonify(data), status

def error_json(msg, status=400):
    return jsonify({"error": str(msg)}), status

# ── CONFIG ────────────────────────────────────────────────────────────────────

CONFIG_FILE = Path(__file__).parent / "dms_config.json"

DEFAULT_CONFIG = {
    "qms_root":        "",
    "current_user":    "",
    "current_email":   "",
    "company_name":    "[COMPANY NAME]",
    # Client-customizable structure
    "company_code":    "CO",          # e.g. ABC → part numbers ABC-P01-M001
    "client_name":     "",            # client/project name for multi-client deployments
    "active_folders":  [              # which QMS folders are enabled for this client
        "01_QUALITY_MANUAL",
        "02_SOPs",
        "03_WORK_INSTRUCTIONS",
        "04_FORMS_TEMPLATES",
        "05_RISK_MANAGEMENT",
        "06_DESIGN_CONTROL",
        "07_SUPPLIER_MANAGEMENT",
        "08_CAPA",
        "09_AUDIT",
        "10_TRAINING",
        "11_CHANGE_REQUESTS",
    ],
    "folder_labels": {                # client can rename folders
        "01_QUALITY_MANUAL":      "01_QUALITY_MANUAL",
        "02_SOPs":                "02_SOPs",
        "03_WORK_INSTRUCTIONS":   "03_WORK_INSTRUCTIONS",
        "04_FORMS_TEMPLATES":     "04_FORMS_TEMPLATES",
        "05_RISK_MANAGEMENT":     "05_RISK_MANAGEMENT",
        "06_DESIGN_CONTROL":      "06_DESIGN_CONTROL",
        "07_SUPPLIER_MANAGEMENT": "07_SUPPLIER_MANAGEMENT",
        "08_CAPA":                "08_CAPA",
        "09_AUDIT":               "09_AUDIT",
        "10_TRAINING":            "10_TRAINING",
        "11_CHANGE_REQUESTS":     "11_CHANGE_REQUESTS",
    },
    "prefix_scheme": {                # client can remap or add prefixes
        "QM":  "Quality Manual",
        "SOP": "Standard Operating Procedure",
        "WI":  "Work Instruction",
        "FM":  "Form / Template",
        "SP":  "Specification",
        "RM":  "Risk Management",
        "DC":  "Design Control",
        "CA":  "CAPA",
        "AU":  "Audit",
        "TR":  "Training Record",
        "SUP": "Supplier Document",
        "CR":  "Change Request",
        "LBL": "Label / Labeling",
        "VAL": "Validation",
        "DWG": "Engineering Drawing",
    },
    "informal_prefix_scheme": {       # prefixes for NOT UNDER QMS docs
        "FS":  "Feasibility Study",
        "BD":  "Business Development",
        "MM":  "Meeting Minutes",
        "PP":  "Project Plan",
        "TR2": "Trip Report",
        "INT": "Internal Memo",
        "REF": "Reference Document",
    },
    "informal_folder": "INFORMAL_DOCS",  # root folder for informal docs
    # Appearance settings (applied to generated document templates)
    "header_color":    "003F7F",    # hex color for formal doc header backgrounds
    "cr_color":        "8B1A00",    # hex color for CR number field
    "doc_font":        "Arial",     # font for document body
    "doc_font_size":   11,          # body font size in points
    "logo_path":       "",          # path to company logo image
    # Document numbering
    "number_padding":         3,       # digits in doc number: 3=SOP-001, 4=SOP-0001
    "project_prefix_style":   "prefix", # "prefix"=P001-SOP-007, "suffix"=SOP-007-P001, "none"=SOP-007
    # Projects registry
    "projects": {},                 # {"P001": "Device Name", "P002": "Another Device"}
}

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                stored = json.load(f)
            # Merge with defaults so new keys appear for existing installs
            merged = {**DEFAULT_CONFIG, **stored}
            # Deep merge nested dicts
            for k in ["folder_labels", "prefix_scheme", "informal_prefix_scheme"]:
                if k in DEFAULT_CONFIG:
                    merged[k] = {**DEFAULT_CONFIG[k], **stored.get(k, {})}
            return merged
        except Exception:
            return dict(DEFAULT_CONFIG)
    return dict(DEFAULT_CONFIG)

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def get_root():
    r = load_config().get("qms_root", "")
    if r and Path(r).exists():
        return Path(r)
    return None

def get_router():
    root = get_root()
    return RoutingEngine(root) if root else None

def get_cr_engine():
    root = get_root()
    return CREngine(root) if root else None

# ── REGISTER HELPERS ──────────────────────────────────────────────────────────

REGISTER_FIELDS = [
    "doc_id", "title", "type", "version", "status", "doc_category",
    "owner", "created_date", "last_modified", "approved_date", "approved_by",
    "effective_date", "next_review_date", "related_docs",
    "iso_13485_clause", "iso_9001_clause", "iso_14971_clause",
    "cr_id", "supersedes", "file_path", "pdf_path", "notes"
]

# doc_category values
DOC_CATEGORY = {
    "FORMAL":   "FORMAL",          # Full QMS lifecycle
    "INFORMAL": "NOT UNDER QMS",   # Lightweight lifecycle
}

# Document status by category
FORMAL_STATUS = {
    "DRAFT":            "DRAFT",
    "IN_REVIEW":        "IN_REVIEW",
    "APPROVED_PENDING": "APPROVED_PENDING",
    "EFFECTIVE":        "EFFECTIVE",
    "OBSOLETE":         "OBSOLETE",
}

INFORMAL_STATUS = {
    "DRAFT":     "DRAFT",
    "IN_REVIEW": "IN_REVIEW",
    "APPROVED":  "APPROVED",      # No APPROVED_PENDING — no CR required
    "SUPERSEDED":"SUPERSEDED",    # Replaced by newer version
}

def get_doc_types():
    return load_config().get("prefix_scheme", DEFAULT_CONFIG["prefix_scheme"])

def get_informal_types():
    return load_config().get("informal_prefix_scheme",
                             DEFAULT_CONFIG["informal_prefix_scheme"])

def get_folder_map():
    cfg     = load_config()
    labels  = cfg.get("folder_labels", {})
    default = {
        "QM":  "01_QUALITY_MANUAL",
        "SOP": "02_SOPs",
        "WI":  "03_WORK_INSTRUCTIONS",
        "FM":  "04_FORMS_TEMPLATES",
        "SP":  "04_FORMS_TEMPLATES",
        "RM":  "05_RISK_MANAGEMENT",
        "DC":  "06_DESIGN_CONTROL",
        "SUP": "07_SUPPLIER_MANAGEMENT",
        "CA":  "08_CAPA",
        "AU":  "09_AUDIT",
        "TR":  "10_TRAINING",
        "CR":  "11_CHANGE_REQUESTS",
        "LBL": "12_LABELING",
        "VAL": "13_VALIDATION",
        "DWG": "14_DRAWINGS",
    }
    # Apply client folder label overrides
    remapped = {}
    for prefix, default_folder in default.items():
        remapped[prefix] = labels.get(default_folder, default_folder)
    return remapped

def register_path():
    root = get_root()
    return (root / "_REGISTER" / "document_register.csv") if root else None

def log_path():
    root = get_root()
    return (root / "_REGISTER" / "audit_log.json") if root else None

def load_register():
    rp = register_path()
    if not rp or not rp.exists() or rp.stat().st_size == 0:
        return []
    try:
        with open(rp, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        # Normalize legacy statuses
        for r in rows:
            if r.get("status") == "APPROVED" and r.get("doc_category") == "FORMAL":
                r["status"] = "EFFECTIVE"
            if "doc_category" not in r or not r["doc_category"]:
                r["doc_category"] = "FORMAL"
        return rows
    except Exception as e:
        print(f"Register load error: {e}")
        return []

def save_register(rows):
    rp = register_path()
    if not rp:
        return
    try:
        with open(rp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=REGISTER_FIELDS, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
    except Exception as e:
        print(f"Register save error: {e}")

def log_action(action, doc_id, user, details=""):
    lp = log_path()
    if not lp:
        return
    log = []
    if lp.exists():
        try:
            with open(lp) as f:
                log = json.load(f)
        except Exception:
            log = []
    log.append({
        "timestamp": datetime.datetime.now().isoformat(),
        "action":    action,
        "doc_id":    doc_id,
        "user":      user,
        "details":   details
    })
    try:
        with open(lp, "w") as f:
            json.dump(log, f, indent=2)
    except Exception as e:
        print(f"Audit log error: {e}")

def next_doc_id(prefix, project_code=""):
    """
    Generate next sequential document ID.
    With project_prefix_style="prefix":  P001-SOP-007
    With project_prefix_style="suffix":  SOP-007-P001
    With project_prefix_style="none":    SOP-007
    Without project_code:                SOP-007
    """
    cfg     = load_config()
    padding = int(cfg.get("number_padding", 3))
    style   = cfg.get("project_prefix_style", "prefix")
    rows    = load_register()

    # Find existing numbers for this prefix (accounting for any project prefix/suffix)
    nums = []
    for r in rows:
        did = r["doc_id"]
        # Extract the core prefix-NNN part
        parts = did.split("-")
        for i, part in enumerate(parts):
            if part == prefix and i+1 < len(parts) and parts[i+1].isdigit():
                nums.append(int(parts[i+1]))
                break

    next_num = str(max(nums) + 1 if nums else 1).zfill(padding)
    base_id  = f"{prefix}-{next_num}"

    if not project_code:
        return base_id
    if style == "prefix":
        return f"{project_code}-{base_id}"     # P001-SOP-007
    elif style == "suffix":
        return f"{base_id}-{project_code}"     # SOP-007-P001
    else:
        return base_id                          # SOP-007 (ignore project code in ID)

def safe_fn(s):
    return re.sub(r'[^a-zA-Z0-9_\- ]', '', s).strip().replace(" ", "_")

# ── CORE ROUTES ───────────────────────────────────────────────────────────────

@app.route("/ping")
def ping():
    return jsonify({"status": "ok", "version": "1.4"})

@app.route("/config", methods=["GET", "POST"])
def config():
    try:
        if request.method == "POST":
            data = request.get_json(force=True, silent=True) or {}
            cfg  = load_config()
            cfg.update(data)
            save_config(cfg)
            return jsonify({"ok": True})
        return jsonify(load_config())
    except Exception as e:
        return error_json(str(e))

@app.route("/config/folders", methods=["GET", "POST"])
def config_folders():
    """Get or update active folders and folder labels."""
    try:
        cfg = load_config()
        if request.method == "POST":
            data = request.get_json(force=True, silent=True) or {}
            if "active_folders" in data:
                cfg["active_folders"] = data["active_folders"]
            if "folder_labels" in data:
                cfg["folder_labels"] = {**cfg.get("folder_labels", {}),
                                        **data["folder_labels"]}
            save_config(cfg)
            return jsonify({"ok": True,
                            "active_folders": cfg["active_folders"],
                            "folder_labels":  cfg["folder_labels"]})
        return jsonify({
            "active_folders": cfg.get("active_folders", []),
            "folder_labels":  cfg.get("folder_labels", {}),
        })
    except Exception as e:
        return error_json(str(e))

@app.route("/config/prefixes", methods=["GET", "POST"])
def config_prefixes():
    """Get or update document prefix schemes."""
    try:
        cfg = load_config()
        if request.method == "POST":
            data = request.get_json(force=True, silent=True) or {}
            if "prefix_scheme" in data:
                cfg["prefix_scheme"] = {**cfg.get("prefix_scheme", {}),
                                        **data["prefix_scheme"]}
            if "informal_prefix_scheme" in data:
                cfg["informal_prefix_scheme"] = {
                    **cfg.get("informal_prefix_scheme", {}),
                    **data["informal_prefix_scheme"]}
            save_config(cfg)
            return jsonify({"ok": True})
        return jsonify({
            "prefix_scheme":          cfg.get("prefix_scheme", {}),
            "informal_prefix_scheme": cfg.get("informal_prefix_scheme", {}),
        })
    except Exception as e:
        return error_json(str(e))

@app.route("/documents", methods=["GET"])
def documents():
    try:
        rows     = load_register()
        status   = request.args.get("status")
        dtype    = request.args.get("type")
        search   = request.args.get("search", "").lower()
        cr_id    = request.args.get("cr_id")
        category = request.args.get("category")   # FORMAL or NOT UNDER QMS
        if status:   rows = [r for r in rows if r["status"] == status.upper()]
        if dtype:    rows = [r for r in rows if r["doc_id"].startswith(dtype.upper() + "-")]
        if search:   rows = [r for r in rows
                             if search in r["title"].lower() or
                             search in r["doc_id"].lower()]
        if cr_id:    rows = [r for r in rows if r.get("cr_id", "") == cr_id]
        if category: rows = [r for r in rows if r.get("doc_category", "FORMAL") == category]
        return jsonify(rows)
    except Exception as e:
        return error_json(str(e))

@app.route("/documents/<doc_id>", methods=["GET"])
def document(doc_id):
    try:
        rows  = load_register()
        match = [r for r in rows if r["doc_id"] == doc_id]
        if match:
            return jsonify(match[0])
        return error_json("Document not found", 404)
    except Exception as e:
        return error_json(str(e))

@app.route("/documents/new", methods=["POST"])
def new_document():
    try:
        root = get_root()
        if not root:
            return error_json("QMS Root Folder is not configured. "
                              "Go to Settings and set the QMS Root Folder first.")
        data     = request.get_json(force=True, silent=True) or {}
        prefix   = data.get("type", "SOP").upper()
        title    = data.get("title", "Untitled")
        owner    = data.get("owner", load_config().get("current_user", "QA User"))
        category = data.get("doc_category", "FORMAL")
        cr_id    = data.get("cr_id", "")
        today    = datetime.date.today().isoformat()

        cfg          = load_config()
        all_types    = {**get_doc_types(), **get_informal_types()}
        doc_type_str = all_types.get(prefix, prefix)

        if category == "FORMAL":
            folder_map = get_folder_map()
            base_folder = root / folder_map.get(prefix, "00_SYSTEM")
        else:
            base_folder = root / cfg.get("informal_folder", "INFORMAL_DOCS")

        folder = base_folder / "Draft"
        folder.mkdir(parents=True, exist_ok=True)

        project_code = data.get("project_code", "")
        doc_id   = next_doc_id(prefix, project_code)
        fname    = f"{doc_id}_RevA_{safe_fn(title)}_DRAFT.docx"
        fpath    = folder / fname

        row = {f: "" for f in REGISTER_FIELDS}
        row.update({
            "doc_id":           doc_id,
            "title":            title,
            "type":             doc_type_str,
            "version":          "A",
            "status":           "DRAFT",
            "doc_category":     category,
            "owner":            owner,
            "created_date":     today,
            "last_modified":    today,
            "iso_13485_clause": data.get("clause_13485", ""),
            "iso_9001_clause":  data.get("clause_9001",  ""),
            "iso_14971_clause": data.get("clause_14971", ""),
            "related_docs":     data.get("related", ""),
            "cr_id":            cr_id,
            "file_path":        str(fpath.relative_to(root)),
            "notes":            f"Created via DMS GUI v1.4 | {category}"
        })
        rows = load_register()
        rows.append(row)
        save_register(rows)

        # Generate template
        company = cfg.get("company_name", "[COMPANY NAME]")
        if category == "FORMAL":
            _generate_formal_docx(fpath, row, company)
        else:
            _generate_informal_docx(fpath, row, company)

        log_action("NEW", doc_id, owner, f"{category} | {fname}")
        return jsonify({"ok": True, "doc_id": doc_id, "file_path": str(fpath)})
    except Exception as e:
        return error_json(str(e))

@app.route("/documents/import", methods=["POST"])
def import_document():
    """
    Register an existing file into the DMS.
    The file is moved/copied to the correct folder and renamed.
    """
    try:
        root = get_root()
        if not root:
            return error_json("QMS Root Folder not configured.")

        data      = request.get_json(force=True, silent=True) or {}
        src_path  = data.get("source_path", "")
        prefix    = data.get("type", "SOP").upper()
        title     = data.get("title", "")
        owner     = data.get("owner", load_config().get("current_user", ""))
        version   = data.get("version", "A")
        status    = data.get("status", "DRAFT")
        category  = data.get("doc_category", "FORMAL")
        cr_id     = data.get("cr_id", "")
        copy_only = data.get("copy_only", False)  # if True, copy not move
        today     = datetime.date.today().isoformat()

        if not src_path or not Path(src_path).exists():
            return error_json(f"Source file not found: {src_path}")
        if not title:
            return error_json("Title is required for import.")

        src = Path(src_path)
        ext = src.suffix  # preserve original extension

        cfg      = load_config()
        all_types = {**get_doc_types(), **get_informal_types()}
        doc_type  = all_types.get(prefix, prefix)

        # Determine target folder based on status
        if category == "FORMAL":
            folder_map  = get_folder_map()
            base_folder = root / folder_map.get(prefix, "00_SYSTEM")
        else:
            base_folder = root / cfg.get("informal_folder", "INFORMAL_DOCS")

        status_folder_map = {
            "DRAFT":            "Draft",
            "IN_REVIEW":        "In_Review",
            "APPROVED_PENDING": "Approved_Pending",
            "EFFECTIVE":        "Effective",
            "APPROVED":         "Effective" if category == "FORMAL" else "Approved",
        }
        sub = status_folder_map.get(status, "Draft")
        target_dir = base_folder / sub
        target_dir.mkdir(parents=True, exist_ok=True)

        project_code = data.get("project_code", "")
        doc_id   = next_doc_id(prefix, project_code)
        ver_str  = f"Rev{version}"
        status_suffix = status.replace("_", "")
        fname    = f"{doc_id}_{ver_str}_{safe_fn(title)}_{status_suffix}{ext}"
        fpath    = target_dir / fname

        if copy_only:
            shutil.copy2(str(src), str(fpath))
        else:
            shutil.move(str(src), str(fpath))

        row = {f: "" for f in REGISTER_FIELDS}
        row.update({
            "doc_id":           doc_id,
            "title":            title,
            "type":             doc_type,
            "version":          version,
            "status":           status,
            "doc_category":     category,
            "owner":            owner,
            "created_date":     today,
            "last_modified":    today,
            "iso_13485_clause": data.get("clause_13485", ""),
            "iso_9001_clause":  data.get("clause_9001",  ""),
            "iso_14971_clause": data.get("clause_14971", ""),
            "related_docs":     data.get("related", ""),
            "cr_id":            cr_id,
            "file_path":        str(fpath.relative_to(root)),
            "notes":            f"Imported from: {src_path} | Project: {project_code or 'QMS-level'}"
        })
        rows = load_register()
        rows.append(row)
        save_register(rows)
        log_action("IMPORT", doc_id, owner, f"From: {src_path} | {category}")
        return jsonify({"ok": True, "doc_id": doc_id, "file_path": str(fpath)})
    except Exception as e:
        return error_json(str(e))

@app.route("/documents/<doc_id>/promote", methods=["POST"])
def promote(doc_id):
    try:
        root = get_root()
        if not root:
            return error_json("QMS Root Folder not configured.")
        data  = request.get_json(force=True, silent=True) or {}
        to    = data.get("to", "review")
        user  = data.get("user", load_config().get("current_user", "QA User"))
        rows  = load_register()
        match = [r for r in rows if r["doc_id"] == doc_id]
        if not match:
            return error_json(f"Document {doc_id} not found.", 404)

        r        = match[0]
        today    = datetime.date.today().isoformat()
        pfx      = doc_id.split("-")[0]
        category = r.get("doc_category", "FORMAL")

        if category == "FORMAL":
            return _promote_formal(r, rows, root, pfx, to, user, today, data)
        else:
            return _promote_informal(r, rows, root, pfx, to, user, today, data)
    except Exception as e:
        return error_json(str(e))

def _promote_formal(r, rows, root, pfx, to, user, today, data):
    """Full QMS lifecycle promotion."""
    folder_map = get_folder_map()

    if r["status"] == "DRAFT" and to == "review":
        old = root / r["file_path"]
        nf  = root / folder_map.get(pfx, "00_SYSTEM") / "In_Review"
        nf.mkdir(parents=True, exist_ok=True)
        nn  = old.name.replace("_DRAFT", "_INREVIEW")
        np  = nf / nn
        if old.exists(): shutil.move(str(old), str(np))
        r["file_path"] = str(np.relative_to(root))
        r["status"]    = "IN_REVIEW"
        r["last_modified"] = today
        log_action("PROMOTE_TO_REVIEW", r["doc_id"], user)
        save_register(rows)
        return jsonify({"ok": True, "status": "IN_REVIEW"})

    elif r["status"] == "IN_REVIEW" and to == "approved_pending":
        old  = root / r["file_path"]
        nver = "1" if r["version"].isalpha() else str(int(r["version"]) + 1)
        r["version"] = nver; r["status"] = "APPROVED_PENDING"
        r["approved_date"] = today; r["approved_by"] = user
        r["last_modified"] = today
        nf = root / folder_map.get(pfx, "00_SYSTEM") / "Approved_Pending"
        nf.mkdir(parents=True, exist_ok=True)
        nn = f"{r['doc_id']}_Rev{nver}_{safe_fn(r['title'])}_APPR_PENDING.docx"
        np = nf / nn
        if old.exists(): shutil.move(str(old), str(np))
        r["file_path"] = str(np.relative_to(root))
        pdf = _generate_pdf(np, user, r, pending=True)
        if pdf: r["pdf_path"] = str(pdf.relative_to(root))
        log_action("APPROVED_PENDING", r["doc_id"], user, f"Rev{nver}")
        save_register(rows)
        return jsonify({"ok": True, "status": "APPROVED_PENDING", "version": nver})

    elif r["status"] == "APPROVED_PENDING" and to == "effective":
        old      = root / r["file_path"]
        eff_date = data.get("effective_date", today)
        r["status"]           = "EFFECTIVE"
        r["effective_date"]   = eff_date
        r["last_modified"]    = today
        r["next_review_date"] = (
            datetime.date.fromisoformat(eff_date) +
            datetime.timedelta(days=365)).isoformat()
        nf = root / folder_map.get(pfx, "00_SYSTEM") / "Effective"
        nf.mkdir(parents=True, exist_ok=True)
        nn = f"{r['doc_id']}_Rev{r['version']}_{safe_fn(r['title'])}_EFFECTIVE.docx"
        np = nf / nn
        if old.exists(): shutil.move(str(old), str(np))
        r["file_path"] = str(np.relative_to(root))
        pdf = _generate_pdf(np, r["approved_by"], r, pending=False)
        if pdf: r["pdf_path"] = str(pdf.relative_to(root))
        _obsolete_prior(r["doc_id"], r["version"], rows, root, today)
        log_action("MADE_EFFECTIVE", r["doc_id"], user,
                   f"Rev{r['version']} | Effective:{eff_date}")
        save_register(rows)
        return jsonify({"ok": True, "status": "EFFECTIVE",
                        "effective_date": eff_date})
    return error_json(f"Invalid formal transition: {r['status']} → {to}")

def _promote_informal(r, rows, root, pfx, to, user, today, data):
    """
    Informal (NOT UNDER QMS) lifecycle:
    DRAFT → IN_REVIEW → APPROVED → (new version = SUPERSEDED)
    No CR required. No APPROVED_PENDING.
    """
    cfg         = load_config()
    base_folder = root / cfg.get("informal_folder", "INFORMAL_DOCS")

    if r["status"] == "DRAFT" and to == "review":
        old = root / r["file_path"]
        nf  = base_folder / "In_Review"
        nf.mkdir(parents=True, exist_ok=True)
        nn  = old.name.replace("_DRAFT", "_INREVIEW")
        np  = nf / nn
        if old.exists(): shutil.move(str(old), str(np))
        r["file_path"]   = str(np.relative_to(root))
        r["status"]      = "IN_REVIEW"
        r["last_modified"] = today
        log_action("INFORMAL_TO_REVIEW", r["doc_id"], user)
        save_register(rows)
        return jsonify({"ok": True, "status": "IN_REVIEW"})

    elif r["status"] == "IN_REVIEW" and to == "approved":
        old  = root / r["file_path"]
        nver = "1" if r["version"].isalpha() else str(int(r["version"]) + 1)
        r["version"] = nver; r["status"] = "APPROVED"
        r["approved_date"] = today; r["approved_by"] = user
        r["last_modified"] = today
        # Informal: no next_review_date required, but set it anyway
        r["next_review_date"] = (datetime.date.today() +
                                  datetime.timedelta(days=365)).isoformat()
        nf = base_folder / "Approved"
        nf.mkdir(parents=True, exist_ok=True)
        nn = f"{r['doc_id']}_Rev{nver}_{safe_fn(r['title'])}_APPROVED.docx"
        np = nf / nn
        if old.exists(): shutil.move(str(old), str(np))
        r["file_path"] = str(np.relative_to(root))
        # Simple PDF stamp for informal (lighter stamp)
        pdf = _generate_pdf(np, user, r, pending=False, informal=True)
        if pdf: r["pdf_path"] = str(pdf.relative_to(root))
        log_action("INFORMAL_APPROVED", r["doc_id"], user, f"Rev{nver}")
        save_register(rows)
        return jsonify({"ok": True, "status": "APPROVED", "version": nver})

    return error_json(f"Invalid informal transition: {r['status']} → {to}")

def _obsolete_prior(doc_id, current_version, rows, root, today):
    """Archive previous EFFECTIVE version when new one becomes effective."""
    for r in rows:
        if (r["doc_id"] == doc_id and
                r["status"] == "EFFECTIVE" and
                r["version"] != current_version):
            old = root / r["file_path"]
            arc = root / "_ARCHIVE" / doc_id.split("-")[0]
            arc.mkdir(parents=True, exist_ok=True)
            if old.exists():
                shutil.copy2(str(old), str(arc / old.name))
                old.unlink()
            if r.get("pdf_path"):
                pp = root / r["pdf_path"]
                if pp.exists():
                    shutil.copy2(str(pp), str(arc / pp.name))
            r["status"]       = "OBSOLETE"
            r["last_modified"] = today

@app.route("/documents/<doc_id>/attach-cr", methods=["POST"])
def attach_cr(doc_id):
    try:
        data  = request.get_json(force=True, silent=True) or {}
        cr_id = data.get("cr_id", "")
        user  = data.get("user", load_config().get("current_user", ""))
        rows  = load_register()
        for r in rows:
            if r["doc_id"] == doc_id:
                r["cr_id"]       = cr_id
                r["last_modified"] = datetime.date.today().isoformat()
        save_register(rows)
        cre = get_cr_engine()
        if cre and cr_id:
            cre.link_document(cr_id, doc_id, user)
        log_action("CR_ATTACHED", doc_id, user, cr_id)
        return jsonify({"ok": True})
    except Exception as e:
        return error_json(str(e))

@app.route("/documents/<doc_id>/obsolete", methods=["POST"])
def obsolete(doc_id):
    try:
        root = get_root()
        if not root:
            return error_json("QMS Root Folder not configured.")
        data  = request.get_json(force=True, silent=True) or {}
        user  = data.get("user", load_config().get("current_user", "QA User"))
        rows  = load_register()
        for r in rows:
            if r["doc_id"] == doc_id:
                old = root / r["file_path"]
                arc = root / "_ARCHIVE" / doc_id.split("-")[0]
                arc.mkdir(parents=True, exist_ok=True)
                if old.exists():
                    shutil.copy2(str(old), str(arc / old.name))
                    old.unlink()
                if r.get("pdf_path"):
                    pp = root / r["pdf_path"]
                    if pp.exists():
                        shutil.copy2(str(pp), str(arc / pp.name))
                r["status"]       = "OBSOLETE"
                r["last_modified"] = datetime.date.today().isoformat()
                log_action("OBSOLETE", doc_id, user)
                save_register(rows)
                return jsonify({"ok": True})
        return error_json("Document not found", 404)
    except Exception as e:
        return error_json(str(e))

@app.route("/documents/<doc_id>/open", methods=["POST"])
def open_document(doc_id):
    try:
        root  = get_root()
        rows  = load_register()
        match = [r for r in rows if r["doc_id"] == doc_id]
        if not match:
            return error_json("Document not found", 404)
        r     = match[0]
        ftype = (request.get_json(force=True, silent=True) or {}).get("type", "docx")
        path  = root / (r["pdf_path"] if ftype == "pdf" and r.get("pdf_path")
                        else r["file_path"])
        if not path.exists():
            return error_json(f"File not found on disk: {path}")
        os.startfile(str(path))
        return jsonify({"ok": True})
    except Exception as e:
        return error_json(str(e))

@app.route("/review-due", methods=["GET"])
def review_due():
    try:
        days  = int(request.args.get("days", 60))
        rows  = load_register()
        today = datetime.date.today()
        due   = [r for r in rows
                 if r.get("next_review_date") and
                 r["status"] in ("EFFECTIVE", "APPROVED") and
                 datetime.date.fromisoformat(r["next_review_date"]) <=
                 today + datetime.timedelta(days=days)]
        return jsonify(due)
    except Exception as e:
        return error_json(str(e))

@app.route("/audit-log", methods=["GET"])
def audit_log():
    try:
        lp = log_path()
        if not lp or not lp.exists():
            return jsonify([])
        with open(lp) as f:
            log = json.load(f)
        return jsonify(list(reversed(log[-200:])))
    except Exception as e:
        return error_json(str(e))

@app.route("/stats", methods=["GET"])
def stats():
    try:
        rows   = load_register()
        router = get_router()
        cre    = get_cr_engine()
        counts = {
            "DRAFT": 0, "IN_REVIEW": 0, "APPROVED_PENDING": 0,
            "EFFECTIVE": 0, "APPROVED": 0, "OBSOLETE": 0,
            "SUPERSEDED": 0, "total": len(rows)
        }
        informal_count = 0
        for r in rows:
            s = r.get("status", "")
            if s in counts:
                counts[s] += 1
            if r.get("doc_category", "FORMAL") != "FORMAL":
                informal_count += 1
        counts["informal_total"] = informal_count
        due = len([r for r in rows
                   if r.get("next_review_date") and
                   r["status"] in ("EFFECTIVE", "APPROVED") and
                   datetime.date.fromisoformat(r["next_review_date"]) <=
                   datetime.date.today() + datetime.timedelta(days=60)])
        counts["review_due"] = due
        if router:
            counts.update(router.get_stats())
        if cre:
            cs = cre.get_stats()
            counts.update({
                "cr_total":            cs.get("total", 0),
                "cr_pending_effective":cs.get("pending_effective", 0),
                "cr_draft":            cs.get("DRAFT", 0),
                "cr_approved":         cs.get("APPROVED", 0),
            })
        return jsonify(counts)
    except Exception as e:
        return error_json(str(e))

# ── ROSTER ROUTES (updated for multi-role) ────────────────────────────────────

@app.route("/roster", methods=["GET"])
def roster():
    try:
        router = get_router()
        if not router:
            return error_json("QMS Root Folder not configured. "
                              "Go to Settings to set it up.")
        return jsonify(router.get_members())
    except Exception as e:
        return error_json(str(e))

@app.route("/roster/add", methods=["POST"])
def roster_add():
    try:
        router = get_router()
        if not router:
            return error_json("QMS Root Folder not configured.")
        data   = request.get_json(force=True, silent=True) or {}
        name   = data.get("name", "").strip()
        email  = data.get("email", "").strip()
        if not name or not email:
            return error_json("Name and email are required.")
        # Accept 'roles' (list) or legacy 'role' (string)
        roles = data.get("roles", data.get("role", ["Reviewer"]))
        if isinstance(roles, str):
            roles = [roles]
        result = router.add_member(
            name=name, email=email,
            roles=roles,
            doc_types=data.get("doc_types", [])
        )
        return jsonify(result)
    except Exception as e:
        return error_json(str(e))

@app.route("/roster/update", methods=["POST"])
def roster_update():
    try:
        router = get_router()
        if not router:
            return error_json("QMS Root Folder not configured.")
        data      = request.get_json(force=True, silent=True) or {}
        member_id = data.get("member_id")
        updates   = data.get("updates", {})
        changed_by = data.get("changed_by",
                               load_config().get("current_user", "System"))
        reason    = data.get("reason", "")
        if not member_id:
            return error_json("member_id is required.")
        return jsonify(router.update_member(member_id, updates, changed_by, reason))
    except Exception as e:
        return error_json(str(e))

@app.route("/roster/remove", methods=["POST"])
def roster_remove():
    try:
        router = get_router()
        if not router:
            return error_json("QMS Root Folder not configured.")
        data = request.get_json(force=True, silent=True) or {}
        return jsonify(router.remove_member(data.get("member_id")))
    except Exception as e:
        return error_json(str(e))

@app.route("/roster/defaults", methods=["GET"])
def roster_defaults():
    try:
        router   = get_router()
        if not router:
            return jsonify({"reviewers": [], "approver": None})
        doc_type = request.args.get("doc_type", "")
        return jsonify({
            "reviewers": router.get_default_reviewers(doc_type),
            "approver":  router.get_default_approver(doc_type),
        })
    except Exception as e:
        return error_json(str(e))

@app.route("/roster/<member_id>/role-history", methods=["GET"])
def member_role_history(member_id):
    try:
        router = get_router()
        if not router:
            return error_json("QMS Root Folder not configured.")
        return jsonify(router.get_member_role_history(member_id))
    except Exception as e:
        return error_json(str(e))

@app.route("/roster/<member_id>/roles-at-date", methods=["GET"])
def roles_at_date(member_id):
    try:
        router      = get_router()
        target_date = request.args.get("date", datetime.date.today().isoformat())
        if not router:
            return error_json("QMS Root Folder not configured.")
        return jsonify(router.get_roles_at_date(member_id, target_date))
    except Exception as e:
        return error_json(str(e))

# ── ROLE MANAGEMENT ROUTES ────────────────────────────────────────────────────

@app.route("/roles", methods=["GET"])
def get_roles():
    try:
        router = get_router()
        if not router:
            return jsonify(DEFAULT_ROLES)
        return jsonify(router.get_custom_roles())
    except Exception as e:
        return error_json(str(e))

@app.route("/roles/add", methods=["POST"])
def add_role():
    try:
        router = get_router()
        if not router:
            return error_json("QMS Root Folder not configured.")
        data = request.get_json(force=True, silent=True) or {}
        role = data.get("role", "").strip()
        if not role:
            return error_json("Role name is required.")
        return jsonify(router.add_custom_role(role))
    except Exception as e:
        return error_json(str(e))

@app.route("/roles/remove", methods=["POST"])
def remove_role():
    try:
        router = get_router()
        if not router:
            return error_json("QMS Root Folder not configured.")
        data = request.get_json(force=True, silent=True) or {}
        return jsonify(router.remove_custom_role(data.get("role", "")))
    except Exception as e:
        return error_json(str(e))

@app.route("/roles/set", methods=["POST"])
def set_roles():
    try:
        router = get_router()
        if not router:
            return error_json("QMS Root Folder not configured.")
        data  = request.get_json(force=True, silent=True) or {}
        roles = data.get("roles", [])
        return jsonify(router.set_custom_roles(roles))
    except Exception as e:
        return error_json(str(e))

# ── ROUTING PASS-THROUGH ──────────────────────────────────────────────────────

@app.route("/routing/queue", methods=["GET"])
def routing_queue():
    try:
        router = get_router()
        if not router:
            return jsonify([])
        q      = router.load_queue()
        status = request.args.get("status")
        doc_id = request.args.get("doc_id")
        user   = request.args.get("user")
        if status: q = [r for r in q if r["status"] == status.upper()]
        if doc_id: q = [r for r in q if r["doc_id"] == doc_id]
        if user:   q = [r for r in q
                        if r["assigned_to_name"].lower() == user.lower() or
                        r["assigned_by_name"].lower() == user.lower()]
        return jsonify(list(reversed(q)))
    except Exception as e:
        return error_json(str(e))

@app.route("/routing/submit-review", methods=["POST"])
def submit_review():
    try:
        router = get_router()
        if not router:
            return error_json("QMS Root Folder not configured.")
        data  = request.get_json(force=True, silent=True) or {}
        cfg   = load_config()
        rows  = load_register()
        doc   = next((r for r in rows if r["doc_id"] == data.get("doc_id")), None)
        if not doc:
            return error_json("Document not found.")
        created = router.submit_for_review(
            doc_id=data["doc_id"], doc_title=doc["title"],
            doc_version=doc["version"], reviewers=data.get("reviewers", []),
            sender_name=data.get("sender_name", cfg.get("current_user", "")),
            sender_email=data.get("sender_email", cfg.get("current_email", "")),
            notes=data.get("notes", ""),
            due_days=int(data.get("due_days", 7)))
        log_action("ROUTE_FOR_REVIEW", data["doc_id"],
                   data.get("sender_name", ""),
                   f"Assigned to: {', '.join(r['name'] for r in data.get('reviewers', []))}")
        return jsonify({"ok": True, "routes_created": len(created), "routes": created})
    except Exception as e:
        return error_json(str(e))

@app.route("/routing/submit-approval", methods=["POST"])
def submit_approval():
    try:
        router = get_router()
        if not router:
            return error_json("QMS Root Folder not configured.")
        data  = request.get_json(force=True, silent=True) or {}
        cfg   = load_config()
        rows  = load_register()
        doc   = next((r for r in rows if r["doc_id"] == data.get("doc_id")), None)
        if not doc:
            return error_json("Document not found.")
        entry = router.submit_for_approval(
            doc_id=data["doc_id"], doc_title=doc["title"],
            doc_version=doc["version"], approver=data.get("approver", {}),
            sender_name=data.get("sender_name", cfg.get("current_user", "")),
            sender_email=cfg.get("current_email", ""),
            notes=data.get("notes", ""))
        log_action("ROUTE_FOR_APPROVAL", data["doc_id"],
                   data.get("sender_name", ""),
                   data.get("approver", {}).get("name", ""))
        return jsonify({"ok": True, "route": entry})
    except Exception as e:
        return error_json(str(e))

@app.route("/routing/complete-review", methods=["POST"])
def complete_review():
    try:
        router = get_router()
        if not router:
            return error_json("QMS Root Folder not configured.")
        data   = request.get_json(force=True, silent=True) or {}
        cfg    = load_config()
        result = router.complete_review(
            data.get("route_id"),
            data.get("reviewer_name", cfg.get("current_user", "")),
            data.get("notes", ""), data.get("rejected", False))
        log_action("REVIEW_COMPLETE" if not data.get("rejected") else "REVIEW_REJECTED",
                   data.get("doc_id", ""),
                   data.get("reviewer_name", ""), data.get("notes", "")[:100])
        return jsonify(result)
    except Exception as e:
        return error_json(str(e))

@app.route("/routing/recall", methods=["POST"])
def recall():
    try:
        router = get_router()
        if not router:
            return error_json("QMS Root Folder not configured.")
        data   = request.get_json(force=True, silent=True) or {}
        cfg    = load_config()
        result = router.recall_route(
            data.get("route_id"),
            data.get("user", cfg.get("current_user", "")))
        log_action("RECALL", data.get("doc_id", ""),
                   data.get("user", ""), data.get("route_id", ""))
        return jsonify(result)
    except Exception as e:
        return error_json(str(e))

@app.route("/routing/broadcast-fyi", methods=["POST"])
def broadcast_fyi():
    try:
        router = get_router()
        if not router:
            return error_json("QMS Root Folder not configured.")
        data   = request.get_json(force=True, silent=True) or {}
        cfg    = load_config()
        result = router.broadcast_fyi(
            doc_id=data.get("doc_id", ""),
            doc_title=data.get("doc_title", ""),
            doc_version=data.get("doc_version", ""),
            recipients=data.get("recipients", []),
            sender_name=data.get("sender_name", cfg.get("current_user", "")),
            notes=data.get("notes", ""))
        return jsonify(result)
    except Exception as e:
        return error_json(str(e))

@app.route("/notifications", methods=["GET"])
def notifications():
    try:
        router = get_router()
        if not router:
            return jsonify([])
        cfg  = load_config()
        return jsonify(router.get_notifications_for_user(
            request.args.get("user", cfg.get("current_user", "")),
            request.args.get("email", cfg.get("current_email", "")),
            request.args.get("include_dismissed", "false").lower() == "true"))
    except Exception as e:
        return error_json(str(e))

@app.route("/notifications/dismiss", methods=["POST"])
def dismiss_notification():
    try:
        router = get_router()
        if not router:
            return error_json("QMS Root Folder not configured.")
        data   = request.get_json(force=True, silent=True) or {}
        cfg    = load_config()
        return jsonify(router.dismiss_notification(
            data.get("notif_id"),
            data.get("user", cfg.get("current_user", ""))))
    except Exception as e:
        return error_json(str(e))

@app.route("/notifications/dismiss-all", methods=["POST"])
def dismiss_all():
    try:
        router = get_router()
        if not router:
            return error_json("QMS Root Folder not configured.")
        cfg    = load_config()
        user   = (request.get_json(force=True, silent=True) or {}).get(
            "user", cfg.get("current_user", ""))
        email  = cfg.get("current_email", "")
        notifs = router.load_notifications()
        for n in notifs:
            if (n["recipient_name"].lower() == user.lower() or
                    (email and n["recipient_email"].lower() == email.lower())):
                n["dismissed"] = True
        router.save_notifications(notifs)
        return jsonify({"ok": True})
    except Exception as e:
        return error_json(str(e))

# ── CR ROUTES (pass-through, error-hardened) ──────────────────────────────────

@app.route("/cr", methods=["GET"])
def list_crs():
    try:
        cre = get_cr_engine()
        if not cre:
            return jsonify([])
        return jsonify(cre.list_crs(status=request.args.get("status")))
    except Exception as e:
        return error_json(str(e))

@app.route("/cr/<cr_id>", methods=["GET"])
def get_cr(cr_id):
    try:
        cre = get_cr_engine()
        if not cre:
            return error_json("QMS Root not configured.", 400)
        cr = cre.get_cr(cr_id)
        if not cr:
            return error_json("CR not found.", 404)
        rows   = load_register()
        linked = []
        for did in [d.strip() for d in cr.get("linked_doc_ids", "").split(",") if d.strip()]:
            m = [r for r in rows if r["doc_id"] == did]
            if m: linked.append(m[0])
        cr["linked_docs_detail"] = linked
        return jsonify(cr)
    except Exception as e:
        return error_json(str(e))

@app.route("/cr/new", methods=["POST"])
def new_cr():
    try:
        cre = get_cr_engine()
        if not cre:
            return error_json("QMS Root not configured.")
        data = request.get_json(force=True, silent=True) or {}
        cfg  = load_config()
        cr   = cre.create_cr(
            title=data.get("title", ""),
            description=data.get("description", ""),
            reason=data.get("reason", ""),
            change_type=data.get("change_type", "Process Change"),
            initiator=data.get("initiator", cfg.get("current_user", "")),
            initiator_email=data.get("initiator_email", cfg.get("current_email", "")),
            linked_doc_ids=data.get("linked_doc_ids", []),
            risk_ref=data.get("risk_ref", ""),
            impact_analysis=data.get("impact_analysis", ""),
            training_required=data.get("training_required", "NO"),
            training_notes=data.get("training_notes", ""),
            target_effective_date=data.get("target_effective_date", ""))
        root = get_root()
        if root:
            cr_doc_id   = next_doc_id("CR")
            folder      = root / get_folder_map().get("CR", "11_CHANGE_REQUESTS") / "Draft"
            folder.mkdir(parents=True, exist_ok=True)
            fname       = f"{cr_doc_id}_RevA_{safe_fn(cr['title'])}_DRAFT.docx"
            fpath       = folder / fname
            row         = {f: "" for f in REGISTER_FIELDS}
            row.update({
                "doc_id": cr_doc_id, "title": f"CR Form — {cr['title']}",
                "type": "Change Request", "version": "A",
                "status": "DRAFT", "doc_category": "FORMAL",
                "owner": cr["initiator"],
                "created_date": datetime.date.today().isoformat(),
                "last_modified": datetime.date.today().isoformat(),
                "cr_id": cr["cr_id"],
                "file_path": str(fpath.relative_to(root)),
                "notes": f"CR Form for {cr['cr_id']}"
            })
            rows = load_register(); rows.append(row); save_register(rows)
            cre.update_cr(cr["cr_id"], {"cr_form_doc_id": cr_doc_id}, cr["initiator"])
            _generate_cr_form(fpath, cr, cfg.get("company_name", "[COMPANY NAME]"), cr_doc_id)
            cr["cr_form_doc_id"] = cr_doc_id
        log_action("CR_CREATED", cr["cr_id"], cr["initiator"], cr["title"])
        return jsonify({"ok": True, "cr": cr})
    except Exception as e:
        return error_json(str(e))

@app.route("/cr/<cr_id>/update", methods=["POST"])
def update_cr(cr_id):
    try:
        cre  = get_cr_engine()
        if not cre: return error_json("QMS Root not configured.")
        data = request.get_json(force=True, silent=True) or {}
        user = data.pop("user", load_config().get("current_user", ""))
        return jsonify(cre.update_cr(cr_id, data, user))
    except Exception as e:
        return error_json(str(e))

@app.route("/cr/<cr_id>/link-doc",   methods=["POST"])
def link_doc(cr_id):
    try:
        cre  = get_cr_engine()
        if not cre: return error_json("QMS Root not configured.")
        data   = request.get_json(force=True, silent=True) or {}
        doc_id = data.get("doc_id", "")
        user   = data.get("user", load_config().get("current_user", ""))
        rows   = load_register()
        for r in rows:
            if r["doc_id"] == doc_id:
                r["cr_id"] = cr_id
                r["last_modified"] = datetime.date.today().isoformat()
        save_register(rows)
        return jsonify(cre.link_document(cr_id, doc_id, user))
    except Exception as e:
        return error_json(str(e))

@app.route("/cr/<cr_id>/unlink-doc", methods=["POST"])
def unlink_doc(cr_id):
    try:
        cre  = get_cr_engine()
        if not cre: return error_json("QMS Root not configured.")
        data = request.get_json(force=True, silent=True) or {}
        return jsonify(cre.unlink_document(
            cr_id, data.get("doc_id", ""),
            data.get("user", load_config().get("current_user", ""))))
    except Exception as e:
        return error_json(str(e))

@app.route("/cr/<cr_id>/submit-review", methods=["POST"])
def cr_submit_review(cr_id):
    try:
        cre  = get_cr_engine()
        if not cre: return error_json("QMS Root not configured.")
        user = (request.get_json(force=True, silent=True) or {}).get(
            "user", load_config().get("current_user", ""))
        result = cre.submit_cr_for_review(cr_id, user)
        log_action("CR_SUBMITTED_FOR_REVIEW", cr_id, user)
        return jsonify(result)
    except Exception as e:
        return error_json(str(e))

@app.route("/cr/<cr_id>/approve", methods=["POST"])
def approve_cr(cr_id):
    try:
        cre  = get_cr_engine()
        if not cre: return error_json("QMS Root not configured.")
        data   = request.get_json(force=True, silent=True) or {}
        user   = data.get("approver", load_config().get("current_user", ""))
        result = cre.approve_cr(cr_id, user, data.get("effective_date", ""))
        if result.get("ok"):
            log_action("CR_APPROVED", cr_id, user,
                       f"Docs: {','.join(result.get('linked_docs', []))}")
        return jsonify(result)
    except Exception as e:
        return error_json(str(e))

@app.route("/cr/<cr_id>/make-effective", methods=["POST"])
def make_effective(cr_id):
    try:
        cre  = get_cr_engine()
        if not cre: return error_json("QMS Root not configured.")
        root = get_root()
        data = request.get_json(force=True, silent=True) or {}
        user = data.get("user", load_config().get("current_user", ""))
        eff  = data.get("effective_date", datetime.date.today().isoformat())
        result = cre.make_effective(cr_id, user, eff)
        if result.get("ok"):
            for did in result.get("linked_docs", []):
                rows  = load_register()
                match = [r for r in rows if r["doc_id"] == did]
                if match and match[0]["status"] == "APPROVED_PENDING":
                    r2 = match[0]
                    pfx = did.split("-")[0]
                    old = root / r2["file_path"]
                    r2["status"]           = "EFFECTIVE"
                    r2["effective_date"]   = eff
                    r2["last_modified"]    = eff
                    r2["next_review_date"] = (
                        datetime.date.fromisoformat(eff) +
                        datetime.timedelta(days=365)).isoformat()
                    nf = root / get_folder_map().get(pfx, "00_SYSTEM") / "Effective"
                    nf.mkdir(parents=True, exist_ok=True)
                    nn = f"{did}_Rev{r2['version']}_{safe_fn(r2['title'])}_EFFECTIVE.docx"
                    np = nf / nn
                    if old.exists(): shutil.move(str(old), str(np))
                    r2["file_path"] = str(np.relative_to(root))
                    pdf = _generate_pdf(np, r2["approved_by"], r2, pending=False)
                    if pdf: r2["pdf_path"] = str(pdf.relative_to(root))
                    _obsolete_prior(did, r2["version"], rows, root, eff)
                    save_register(rows)
                    log_action("MADE_EFFECTIVE", did, user,
                               f"CR:{cr_id} | Rev{r2['version']}")
            router = get_router()
            if router:
                cr_obj  = cre.get_cr(cr_id)
                members = router.get_members()
                if cr_obj and members:
                    router.broadcast_fyi(
                        doc_id=cr_id, doc_title=cr_obj.get("title", ""),
                        doc_version="",
                        recipients=[m for m in members if m.get("active")],
                        sender_name=user,
                        notes=f"{cr_id} is now EFFECTIVE as of {eff}.")
        return jsonify(result)
    except Exception as e:
        return error_json(str(e))

@app.route("/cr/<cr_id>/close",  methods=["POST"])
def close_cr(cr_id):
    try:
        cre  = get_cr_engine()
        if not cre: return error_json("QMS Root not configured.")
        data = request.get_json(force=True, silent=True) or {}
        user = data.get("user", load_config().get("current_user", ""))
        result = cre.close_cr(cr_id, user, data.get("post_impl_notes", ""))
        log_action("CR_CLOSED", cr_id, user)
        return jsonify(result)
    except Exception as e:
        return error_json(str(e))

@app.route("/cr/<cr_id>/cancel", methods=["POST"])
def cancel_cr(cr_id):
    try:
        cre  = get_cr_engine()
        if not cre: return error_json("QMS Root not configured.")
        data = request.get_json(force=True, silent=True) or {}
        user = data.get("user", load_config().get("current_user", ""))
        result = cre.cancel_cr(cr_id, user, data.get("reason", ""))
        log_action("CR_CANCELLED", cr_id, user, data.get("reason", ""))
        return jsonify(result)
    except Exception as e:
        return error_json(str(e))

@app.route("/cr/pending-effective", methods=["GET"])
def pending_effective():
    try:
        cre = get_cr_engine()
        return jsonify(cre.get_pending_effective() if cre else [])
    except Exception as e:
        return error_json(str(e))

@app.route("/cr/log", methods=["GET"])
def cr_log():
    try:
        cre = get_cr_engine()
        if not cre: return jsonify([])
        return jsonify(cre.get_log(request.args.get("cr_id")))
    except Exception as e:
        return error_json(str(e))

@app.route("/doc-id-from-filename", methods=["POST"])
def doc_id_from_filename():
    try:
        filename = (request.get_json(force=True, silent=True) or {}).get("filename", "")
        rows     = load_register()
        for r in rows:
            if (Path(r.get("file_path", "")).name == filename or
                    r["doc_id"] in filename):
                return jsonify(r)
        return error_json("Not found", 404)
    except Exception as e:
        return error_json(str(e))

# ── DOCX GENERATION ───────────────────────────────────────────────────────────

def _generate_formal_docx(filepath, reg_row, company_name):
    """Generate full QMS controlled document template."""
    cfg = load_config()
    ti  = reg_row['title'].replace("'", "\\'")
    ow  = reg_row['owner'].replace("'", "\\'")
    co  = company_name.replace("'", "\\'")
    cr  = reg_row.get('cr_id', '') or 'N/A'
    c13 = reg_row.get('iso_13485_clause', '') or 'N/A'
    c9  = reg_row.get('iso_9001_clause',  '') or 'N/A'
    c14 = reg_row.get('iso_14971_clause', '') or 'N/A'
    rel = (reg_row.get('related_docs', '') or 'None specified').replace("'", "\\'")
    sup = (reg_row.get('supersedes', '') or '—').replace("'", "\\'")
    # Client appearance settings
    hdr_color = cfg.get('header_color', '003F7F')
    cr_color  = cfg.get('cr_color',     '8B1A00')
    doc_font  = cfg.get('doc_font',     'Arial')
    font_sz   = int(cfg.get('doc_font_size', 11)) * 2  # docx uses half-points

    script = f"""
const {{Document,Packer,Paragraph,TextRun,Table,TableRow,TableCell,
        AlignmentType,HeadingLevel,BorderStyle,WidthType,ShadingType}}=require('docx');
const fs=require('fs');
const b={{style:BorderStyle.SINGLE,size:1,color:'CCCCCC'}};
const bs={{top:b,bottom:b,left:b,right:b}};
const hc=(t,f,w)=>new TableCell({{borders:bs,width:{{size:w,type:WidthType.DXA}},
  shading:{{fill:f||'{hdr_color}',type:ShadingType.CLEAR}},margins:{{top:80,bottom:80,left:120,right:120}},
  children:[new Paragraph({{children:[new TextRun({{text:t,bold:true,color:'FFFFFF',size:18,font:'{doc_font}'}})]}})]
}});
const dc=(t,w,c)=>new TableCell({{borders:bs,width:{{size:w,type:WidthType.DXA}},
  margins:{{top:80,bottom:80,left:120,right:120}},
  children:[new Paragraph({{children:[new TextRun({{text:t,size:18,font:'{doc_font}',color:c||'222222'}})]}})]
}});
const sc=(label,w)=>new TableCell({{borders:bs,width:{{size:w,type:WidthType.DXA}},
  margins:{{top:100,bottom:100,left:120,right:120}},
  children:[
    new Paragraph({{children:[new TextRun({{text:label,bold:true,size:16,font:'{doc_font}'}})]}})
    ,new Paragraph({{children:[new TextRun({{text:'Name / Title:',size:16,font:'{doc_font}',color:'555555'}})]}})
    ,new Paragraph({{children:[new TextRun({{text:' ',size:22}})]}})
    ,new Paragraph({{children:[new TextRun({{text:'Date: ___________',size:16,font:'{doc_font}',color:'555555'}})]}})
    ,new Paragraph({{children:[new TextRun({{text:'Signature: ________________________',size:16,font:'{doc_font}',color:'555555'}})]}})
  ]
}});
const doc=new Document({{
  styles:{{default:{{document:{{run:{{font:'{doc_font}',size:22}}}}}},
    paragraphStyles:[
      {{id:'Heading1',name:'Heading 1',basedOn:'Normal',next:'Normal',quickFormat:true,
        run:{{size:28,bold:true,font:'{doc_font}',color:'003F7F'}},
        paragraph:{{spacing:{{before:280,after:120}},outlineLevel:0}}}},
      {{id:'Heading2',name:'Heading 2',basedOn:'Normal',next:'Normal',quickFormat:true,
        run:{{size:22,bold:true,font:'{doc_font}',color:'003F7F'}},
        paragraph:{{spacing:{{before:180,after:80}},outlineLevel:1}}}},
    ]}},
  sections:[{{
    properties:{{page:{{size:{{width:12240,height:15840}},margin:{{top:1008,right:1008,bottom:1008,left:1008}}}}}},
    children:[
      new Paragraph({{alignment:AlignmentType.CENTER,
        border:{{bottom:{{style:BorderStyle.SINGLE,size:8,color:'003F7F',space:8}}}},spacing:{{after:0}},
        children:[new TextRun({{text:'{co}',bold:true,size:32,font:'{doc_font}',color:'003F7F'}}),
                  new TextRun({{text:'   CONTROLLED DOCUMENT',size:20,font:'{doc_font}',color:'888888'}})]}})
      ,new Paragraph({{children:[new TextRun(' ')],spacing:{{after:60}}}})
      ,new Table({{width:{{size:9360,type:WidthType.DXA}},columnWidths:[2340,2340,2340,2340],rows:[
        new TableRow({{children:[hc('Document ID',undefined,2340),hc('Revision',undefined,2340),hc('CR Number','8B1A00',2340),hc('Status',undefined,2340)]}}),
        new TableRow({{children:[dc('{reg_row["doc_id"]}',2340),dc('Rev {reg_row["version"]}',2340),
          dc('{cr}',2340,'8B1A00'),dc('{reg_row["status"]}',2340)]}})
      ]}})
      ,new Paragraph({{children:[new TextRun(' ')],spacing:{{after:60}}}})
      ,new Table({{width:{{size:9360,type:WidthType.DXA}},columnWidths:[4680,4680],rows:[
        new TableRow({{children:[hc('Document Title',undefined,4680),hc('Document Type',undefined,4680)]}}),
        new TableRow({{children:[dc('{ti}',4680),dc('{reg_row["type"]}',4680)]}}),
        new TableRow({{children:[hc('Owner / Author',undefined,4680),hc('Supersedes',undefined,4680)]}}),
        new TableRow({{children:[dc('{ow}',4680),dc('{sup}',4680)]}}),
        new TableRow({{children:[hc('Effective Date',undefined,4680),hc('Next Review Date',undefined,4680)]}}),
        new TableRow({{children:[dc('[PENDING CR EFFECTIVITY]',4680),dc('[SET ON EFFECTIVITY]',4680)]}})
      ]}})
      ,new Paragraph({{children:[new TextRun(' ')],spacing:{{after:80}}}})
      ,new Paragraph({{heading:HeadingLevel.HEADING_2,children:[new TextRun('Regulatory Mapping')]}})
      ,new Table({{width:{{size:9360,type:WidthType.DXA}},columnWidths:[3120,3120,3120],rows:[
        new TableRow({{children:[hc('ISO 13485:2016','444466',3120),hc('ISO 9001:2015','444466',3120),hc('ISO 14971:2019','444466',3120)]}}),
        new TableRow({{children:[dc('{c13}',3120),dc('{c9}',3120),dc('{c14}',3120)]}})
      ]}})
      ,new Paragraph({{children:[new TextRun(' ')],spacing:{{after:80}}}})
      ,new Paragraph({{heading:HeadingLevel.HEADING_2,children:[new TextRun('Approval Signatures')]}})
      ,new Table({{width:{{size:9360,type:WidthType.DXA}},columnWidths:[3120,3120,3120],rows:[
        new TableRow({{children:[hc('Prepared By','2D6A2D',3120),hc('Reviewed By','7A5C00',3120),hc('Approved By','003F7F',3120)]}}),
        new TableRow({{children:[sc('Author',3120),sc('Reviewer',3120),sc('Approver',3120)]}})
      ]}})
      ,new Paragraph({{children:[new TextRun(' ')],spacing:{{after:80}}}})
      ,new Paragraph({{heading:HeadingLevel.HEADING_2,children:[new TextRun('Revision History')]}})
      ,new Table({{width:{{size:9360,type:WidthType.DXA}},columnWidths:[720,1440,1440,3960,1800],rows:[
        new TableRow({{children:[hc('Rev','555555',720),hc('Date','555555',1440),hc('CR','555555',1440),hc('Description','555555',3960),hc('Author','555555',1800)]}}),
        new TableRow({{children:[dc('A',720),dc('[DATE]',1440),dc('{cr}',1440),dc('Initial draft',3960),dc('{ow}',1800)]}})
      ]}})
      ,new Paragraph({{children:[new TextRun(' ')],spacing:{{after:80}}}})
      ,new Paragraph({{heading:HeadingLevel.HEADING_2,children:[new TextRun('Related Documents')]}})
      ,new Paragraph({{children:[new TextRun({{text:'{rel}',size:20,font:'{doc_font}'}})]}})
      ,new Paragraph({{children:[new TextRun(' ')],spacing:{{after:180}}}})
      ,new Paragraph({{heading:HeadingLevel.HEADING_1,children:[new TextRun('1. Purpose')]}})
      ,new Paragraph({{children:[new TextRun({{text:'[Describe the purpose of this document.]',size:20,font:'{doc_font}',color:'AAAAAA',italics:true}})]}})
      ,new Paragraph({{children:[new TextRun(' ')],spacing:{{after:80}}}})
      ,new Paragraph({{heading:HeadingLevel.HEADING_1,children:[new TextRun('2. Scope')]}})
      ,new Paragraph({{children:[new TextRun({{text:'[Define scope — products, processes, departments, phases.]',size:20,font:'{doc_font}',color:'AAAAAA',italics:true}})]}})
      ,new Paragraph({{children:[new TextRun(' ')],spacing:{{after:80}}}})
      ,new Paragraph({{heading:HeadingLevel.HEADING_1,children:[new TextRun('3. Definitions & Abbreviations')]}})
      ,new Paragraph({{children:[new TextRun({{text:'[Key terms and acronyms.]',size:20,font:'{doc_font}',color:'AAAAAA',italics:true}})]}})
      ,new Paragraph({{children:[new TextRun(' ')],spacing:{{after:80}}}})
      ,new Paragraph({{heading:HeadingLevel.HEADING_1,children:[new TextRun('4. Responsibilities')]}})
      ,new Paragraph({{children:[new TextRun({{text:'[Who owns, executes, and reviews this process.]',size:20,font:'{doc_font}',color:'AAAAAA',italics:true}})]}})
      ,new Paragraph({{children:[new TextRun(' ')],spacing:{{after:80}}}})
      ,new Paragraph({{heading:HeadingLevel.HEADING_1,children:[new TextRun('5. Procedure / Content')]}})
      ,new Paragraph({{children:[new TextRun({{text:'[Main body — steps, requirements, acceptance criteria.]',size:20,font:'{doc_font}',color:'AAAAAA',italics:true}})]}})
      ,new Paragraph({{children:[new TextRun(' ')],spacing:{{after:80}}}})
      ,new Paragraph({{heading:HeadingLevel.HEADING_1,children:[new TextRun('6. Records & Retention')]}})
      ,new Paragraph({{children:[new TextRun({{text:'[Records generated, retained, and for how long.]',size:20,font:'{doc_font}',color:'AAAAAA',italics:true}})]}})
      ,new Paragraph({{children:[new TextRun(' ')],spacing:{{after:80}}}})
      ,new Paragraph({{heading:HeadingLevel.HEADING_1,children:[new TextRun('7. References')]}})
      ,new Paragraph({{children:[new TextRun({{text:'[External standards and internal cross-references.]',size:20,font:'{doc_font}',color:'AAAAAA',italics:true}})]}})
    ]
  }}]
}});
Packer.toBuffer(doc).then(buf=>{{fs.writeFileSync('{str(filepath)}',buf);console.log('OK');}});
"""
    _run_node(filepath, script)

def _generate_informal_docx(filepath, reg_row, company_name):
    """Generate a lighter informal document template — NOT UNDER QMS."""
    ti = reg_row['title'].replace("'", "\\'")
    ow = reg_row['owner'].replace("'", "\\'")
    co = company_name.replace("'", "\\'")

    script = f"""
const {{Document,Packer,Paragraph,TextRun,Table,TableRow,TableCell,
        AlignmentType,HeadingLevel,BorderStyle,WidthType,ShadingType}}=require('docx');
const fs=require('fs');
const b={{style:BorderStyle.SINGLE,size:1,color:'DDDDDD'}};
const bs={{top:b,bottom:b,left:b,right:b}};
const hc=(t,f,w)=>new TableCell({{borders:bs,width:{{size:w,type:WidthType.DXA}},
  shading:{{fill:f||'3A3A50',type:ShadingType.CLEAR}},margins:{{top:80,bottom:80,left:120,right:120}},
  children:[new Paragraph({{children:[new TextRun({{text:t,bold:true,color:'FFFFFF',size:18,font:'Arial'}})]}})]
}});
const dc=(t,w)=>new TableCell({{borders:bs,width:{{size:w,type:WidthType.DXA}},
  margins:{{top:80,bottom:80,left:120,right:120}},
  children:[new Paragraph({{children:[new TextRun({{text:t,size:18,font:'Arial'}})]}})]
}});
const sc=(label,w)=>new TableCell({{borders:bs,width:{{size:w,type:WidthType.DXA}},
  margins:{{top:100,bottom:100,left:120,right:120}},
  children:[
    new Paragraph({{children:[new TextRun({{text:label,bold:true,size:16,font:'Arial'}})]}})
    ,new Paragraph({{children:[new TextRun({{text:'Name:',size:16,font:'Arial',color:'555555'}})]}})
    ,new Paragraph({{children:[new TextRun({{text:' ',size:22}})]}})
    ,new Paragraph({{children:[new TextRun({{text:'Date: ___________',size:16,font:'Arial',color:'555555'}})]}})
    ,new Paragraph({{children:[new TextRun({{text:'Signature: ________________________',size:16,font:'Arial',color:'555555'}})]}})
  ]
}});
const doc=new Document({{
  styles:{{default:{{document:{{run:{{font:'{doc_font}',size:{font_sz}}}}}}}}},
  sections:[{{
    properties:{{page:{{size:{{width:12240,height:15840}},margin:{{top:1008,right:1008,bottom:1008,left:1008}}}}}},
    children:[
      new Paragraph({{alignment:AlignmentType.CENTER,
        border:{{bottom:{{style:BorderStyle.SINGLE,size:6,color:'3A3A50',space:8}}}},spacing:{{after:0}},
        children:[new TextRun({{text:'{co}',bold:true,size:28,font:'Arial',color:'3A3A50'}}),
                  new TextRun({{text:'   NOT UNDER QMS',size:18,font:'Arial',color:'AA6600',bold:true}})]}})
      ,new Paragraph({{children:[new TextRun(' ')],spacing:{{after:60}}}})
      ,new Table({{width:{{size:9360,type:WidthType.DXA}},columnWidths:[2340,2340,2340,2340],rows:[
        new TableRow({{children:[hc('Document ID',undefined,2340),hc('Revision',undefined,2340),hc('Type',undefined,2340),hc('Status',undefined,2340)]}}),
        new TableRow({{children:[dc('{reg_row["doc_id"]}',2340),dc('Rev {reg_row["version"]}',2340),dc('{reg_row["type"]}',2340),dc('{reg_row["status"]}',2340)]}})
      ]}})
      ,new Paragraph({{children:[new TextRun(' ')],spacing:{{after:60}}}})
      ,new Table({{width:{{size:9360,type:WidthType.DXA}},columnWidths:[4680,4680],rows:[
        new TableRow({{children:[hc('Title',undefined,4680),hc('Author',undefined,4680)]}}),
        new TableRow({{children:[dc('{ti}',4680),dc('{ow}',4680)]}})
      ]}})
      ,new Paragraph({{children:[new TextRun(' ')],spacing:{{after:80}}}})
      ,new Table({{width:{{size:9360,type:WidthType.DXA}},columnWidths:[720,1872,5040,1728],rows:[
        new TableRow({{children:[hc('Rev','555555',720),hc('Date','555555',1872),hc('Description','555555',5040),hc('Author','555555',1728)]}}),
        new TableRow({{children:[dc('A',720),dc('[DATE]',1872),dc('Initial draft',5040),dc('{ow}',1728)]}})
      ]}})
      ,new Paragraph({{children:[new TextRun(' ')],spacing:{{after:80}}}})
      ,new Paragraph({{heading:HeadingLevel.HEADING_2,children:[new TextRun('Review / Sign-off')]}})
      ,new Table({{width:{{size:9360,type:WidthType.DXA}},columnWidths:[4680,4680],rows:[
        new TableRow({{children:[hc('Prepared By',undefined,4680),hc('Reviewed / Approved By',undefined,4680)]}}),
        new TableRow({{children:[sc('Author',4680),sc('Reviewer',4680)]}})
      ]}})
      ,new Paragraph({{children:[new TextRun(' ')],spacing:{{after:160}}}})
      ,new Paragraph({{heading:HeadingLevel.HEADING_1,children:[new TextRun('1. Purpose / Background')]}})
      ,new Paragraph({{children:[new TextRun({{text:'[Describe the purpose or background of this document.]',size:20,font:'Arial',color:'AAAAAA',italics:true}})]}})
      ,new Paragraph({{children:[new TextRun(' ')],spacing:{{after:80}}}})
      ,new Paragraph({{heading:HeadingLevel.HEADING_1,children:[new TextRun('2. Content')]}})
      ,new Paragraph({{children:[new TextRun({{text:'[Main content goes here.]',size:20,font:'Arial',color:'AAAAAA',italics:true}})]}})
      ,new Paragraph({{children:[new TextRun(' ')],spacing:{{after:80}}}})
      ,new Paragraph({{heading:HeadingLevel.HEADING_1,children:[new TextRun('3. Conclusions / Next Steps')]}})
      ,new Paragraph({{children:[new TextRun({{text:'[Summary, conclusions, action items, or next steps.]',size:20,font:'Arial',color:'AAAAAA',italics:true}})]}})
      ,new Paragraph({{children:[new TextRun(' ')],spacing:{{after:80}}}})
      ,new Paragraph({{children:[new TextRun({{text:'NOT UNDER QMS — This document is for internal reference only and is not a controlled quality record.',size:18,font:'Arial',color:'AA6600',bold:true,italics:true}})]}})
    ]
  }}]
}});
Packer.toBuffer(doc).then(buf=>{{fs.writeFileSync('{str(filepath)}',buf);console.log('OK');}});
"""
    _run_node(filepath, script)

def _generate_cr_form(filepath, cr, company_name, cr_doc_id):
    co  = company_name.replace("'", "\\'")
    ti  = cr['title'].replace("'", "\\'")
    ini = cr.get('initiator', '').replace("'", "\\'")
    de  = cr.get('description', '').replace("'", "\\'")
    re_txt = cr.get('reason', '').replace("'", "\\'")
    ct  = cr.get('change_type', '').replace("'", "\\'")
    ted = cr.get('target_effective_date', '[TBD]') or '[TBD]'
    linked = cr.get('linked_doc_ids', 'None') or 'None'

    script = f"""
const {{Document,Packer,Paragraph,TextRun,Table,TableRow,TableCell,
        AlignmentType,BorderStyle,WidthType,ShadingType}}=require('docx');
const fs=require('fs');
const b={{style:BorderStyle.SINGLE,size:1,color:'CCCCCC'}};
const bs={{top:b,bottom:b,left:b,right:b}};
const hc=(t,f,w)=>new TableCell({{borders:bs,width:{{size:w,type:WidthType.DXA}},
  shading:{{fill:f||'8B1A00',type:ShadingType.CLEAR}},margins:{{top:80,bottom:80,left:120,right:120}},
  children:[new Paragraph({{children:[new TextRun({{text:t,bold:true,color:'FFFFFF',size:18,font:'Arial'}})]}})]
}});
const dc=(t,w)=>new TableCell({{borders:bs,width:{{size:w,type:WidthType.DXA}},
  margins:{{top:80,bottom:80,left:120,right:120}},
  children:[new Paragraph({{children:[new TextRun({{text:t||'[Pending]',size:18,font:'Arial'}})]}})]
}});
const sc=(label,w)=>new TableCell({{borders:bs,width:{{size:w,type:WidthType.DXA}},
  margins:{{top:100,bottom:100,left:120,right:120}},
  children:[
    new Paragraph({{children:[new TextRun({{text:label,bold:true,size:16,font:'Arial'}})]}})
    ,new Paragraph({{children:[new TextRun({{text:'Name / Title:',size:16,font:'Arial',color:'555555'}})]}})
    ,new Paragraph({{children:[new TextRun({{text:' ',size:22}})]}})
    ,new Paragraph({{children:[new TextRun({{text:'Date: ___________',size:16,font:'Arial',color:'555555'}})]}})
    ,new Paragraph({{children:[new TextRun({{text:'Signature: ________________________',size:16,font:'Arial',color:'555555'}})]}})
  ]
}});
const doc=new Document({{sections:[{{
  properties:{{page:{{size:{{width:12240,height:15840}},margin:{{top:1008,right:1008,bottom:1008,left:1008}}}}}},
  children:[
    new Paragraph({{alignment:AlignmentType.CENTER,
      border:{{bottom:{{style:BorderStyle.SINGLE,size:8,color:'8B1A00',space:8}}}},spacing:{{after:0}},
      children:[new TextRun({{text:'{co}',bold:true,size:32,font:'Arial',color:'8B1A00'}}),
                new TextRun({{text:'   CHANGE REQUEST FORM',size:20,font:'Arial',color:'888888'}})]}})
    ,new Paragraph({{children:[new TextRun(' ')],spacing:{{after:60}}}})
    ,new Table({{width:{{size:9360,type:WidthType.DXA}},columnWidths:[2340,2340,2340,2340],rows:[
      new TableRow({{children:[hc('CR Number',undefined,2340),hc('Form Doc ID',undefined,2340),hc('Change Type',undefined,2340),hc('Status',undefined,2340)]}}),
      new TableRow({{children:[dc('{cr["cr_id"]}',2340),dc('{cr_doc_id}',2340),dc('{ct}',2340),dc('DRAFT',2340)]}})
    ]}})
    ,new Paragraph({{children:[new TextRun(' ')],spacing:{{after:60}}}})
    ,new Table({{width:{{size:9360,type:WidthType.DXA}},columnWidths:[4680,4680],rows:[
      new TableRow({{children:[hc('CR Title',undefined,4680),hc('Initiator',undefined,4680)]}}),
      new TableRow({{children:[dc('{ti}',4680),dc('{ini}',4680)]}}),
      new TableRow({{children:[hc('Target Effective Date',undefined,4680),hc('Linked Documents',undefined,4680)]}}),
      new TableRow({{children:[dc('{ted}',4680),dc('{linked}',4680)]}})
    ]}})
    ,new Paragraph({{children:[new TextRun(' ')],spacing:{{after:80}}}})
    ,new Table({{width:{{size:9360,type:WidthType.DXA}},columnWidths:[9360],rows:[
      new TableRow({{children:[hc('Description of Change',undefined,9360)]}}),
      new TableRow({{children:[dc('{de}',9360)]}}),
      new TableRow({{children:[hc('Reason / Justification',undefined,9360)]}}),
      new TableRow({{children:[dc('{re_txt}',9360)]}})
    ]}})
    ,new Paragraph({{children:[new TextRun(' ')],spacing:{{after:80}}}})
    ,new Paragraph({{children:[new TextRun({{text:'Approval Signatures',bold:true,size:24,font:'Arial',color:'8B1A00'}})]}})
    ,new Table({{width:{{size:9360,type:WidthType.DXA}},columnWidths:[3120,3120,3120],rows:[
      new TableRow({{children:[hc('Prepared By','2D6A2D',3120),hc('Reviewed By','7A5C00',3120),hc('Approved By','8B1A00',3120)]}}),
      new TableRow({{children:[sc('Initiator',3120),sc('Reviewer',3120),sc('QA Approver',3120)]}})
    ]}})
  ]
}}]}});
Packer.toBuffer(doc).then(buf=>{{fs.writeFileSync('{str(filepath)}',buf);console.log('OK');}});
"""
    _run_node(filepath, script)

def _run_node(filepath, script):
    tmp = filepath.parent / "_gen_tmp.js"
    try:
        tmp.write_text(script)
        result = subprocess.run(["node", str(tmp)], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"Node error: {result.stderr[:300]}")
    except Exception as e:
        print(f"Node run error: {e}")
    finally:
        tmp.unlink(missing_ok=True)

def _generate_pdf(docx_path, signer, reg_row, pending=False, informal=False):
    try:
        subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf",
             str(docx_path), "--outdir", str(docx_path.parent)],
            capture_output=True, timeout=30)
        pdf = docx_path.parent / (docx_path.stem + ".pdf")
        if pdf.exists():
            _stamp_pdf(pdf, signer, reg_row, pending, informal)
            return pdf
    except Exception as e:
        print(f"PDF error: {e}")
    return None

def _stamp_pdf(pdf_path, signer, reg_row, pending=False, informal=False):
    try:
        from reportlab.pdfgen import canvas as rlc
        from reportlab.lib.pagesizes import letter
        from pypdf import PdfReader, PdfWriter
        import io
        reader = PdfReader(str(pdf_path))
        writer = PdfWriter()
        today  = datetime.date.today().isoformat()
        cr_id  = reg_row.get('cr_id', '') or 'N/A'
        if informal:
            label = "NOT UNDER QMS"
            color = (0.67, 0.4, 0)
        elif pending:
            label = "APPROVED — PENDING EFFECTIVITY"
            color = (0.55, 0.1, 0)
        else:
            label = "EFFECTIVE"
            color = (0, 0.25, 0.5)

        for page in reader.pages:
            pkt = io.BytesIO()
            c   = rlc.Canvas(pkt, pagesize=letter)
            c.setFont("Helvetica-Bold", 7)
            c.setFillColorRGB(*color)
            if informal:
                stamp = (f"{label}  |  {reg_row['doc_id']} Rev{reg_row['version']}  |  "
                         f"Approved by: {signer}  |  Date: {today}")
            else:
                stamp = (f"{label}  |  {reg_row['doc_id']} Rev{reg_row['version']}  |  "
                         f"CR: {cr_id}  |  Approved by: {signer}  |  Date: {today}  |  "
                         f"ISO 13485: {reg_row.get('iso_13485_clause', '')}")
            c.drawString(30, 18, stamp)
            c.setStrokeColorRGB(*color)
            c.line(30, 28, 580, 28)
            c.save()
            pkt.seek(0)
            from pypdf import PdfReader as PR2
            page.merge_page(PR2(pkt).pages[0])
            writer.add_page(page)
        with open(str(pdf_path), "wb") as f:
            writer.write(f)
    except Exception as e:
        print(f"Stamp error: {e}")

if __name__ == "__main__":
    print("QMS DMS Server v1.4 — http://localhost:5151")
    app.run(host="0.0.0.0", port=5151, debug=True, use_reloader=True)
