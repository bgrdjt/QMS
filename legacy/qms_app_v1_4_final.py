#!/usr/bin/env python3
"""
QMS Desktop Application v1.4
Adds: Routing panel, Notifications panel, Team Roster panel
"""

import sys, os, subprocess, threading, time
from pathlib import Path
from datetime import datetime, date

try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QStackedWidget, QPushButton, QLabel, QTableWidget, QTableWidgetItem,
        QHeaderView, QLineEdit, QComboBox, QDialog, QDialogButtonBox,
        QFormLayout, QMessageBox, QFileDialog, QFrame, QTextEdit,
        QAbstractItemView, QProgressBar, QCheckBox, QListWidget,
        QListWidgetItem, QSplitter, QScrollArea, QGridLayout, QSpinBox,
        QTabWidget, QSizePolicy
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
    from PyQt5.QtGui import QFont, QColor, QIcon
except ImportError:
    print("PyQt5 not installed. Run: pip install PyQt5"); sys.exit(1)

try:
    import requests
except ImportError:
    print("requests not installed. Run: pip install requests"); sys.exit(1)

API = "http://127.0.0.1:5151"
SERVER_SCRIPT = Path(__file__).parent.parent / "server" / "dms_server.py"
DOC_TYPES = ["QM","SOP","WI","FM","RM","DC","CA","AU","TR","SP"]
ROLES = ["Author","Reviewer","Approver","QA Lead","Observer"]
STATUS_COLORS = {
    "DRAFT":"#E8A020","IN_REVIEW":"#4090FF",
    "APPROVED":"#30C070","OBSOLETE":"#888888"
}
ROUTE_STATUS_COLORS = {
    "PENDING":"#E8A020","ACCEPTED":"#4090FF","REVIEWED":"#30C070",
    "REJECTED":"#FF5050","RECALLED":"#888888","APPROVED":"#30C070","EXPIRED":"#CC4444"
}
NOTIF_COLORS = {
    "REVIEW_REQUESTED":"#4090FF","APPROVAL_REQUESTED":"#E8A020",
    "REVIEW_COMPLETE":"#30C070","REVIEW_REJECTED":"#FF5050",
    "DOCUMENT_APPROVED":"#30C070","FYI":"#8890A8",
    "REVIEW_DUE_SOON":"#E8A020","REVIEW_OVERDUE":"#FF5050"
}

NAV_ITEMS = [
    ("Dashboard",      "⬛", False),
    ("Documents",      "📄", False),
    ("New Document",   "➕", False),
    ("Routing",        "↗",  True),   # True = show badge
    ("Notifications",  "🔔", True),
    ("Team Roster",    "👥", False),
    ("Review Due",     "📅", False),
    ("Audit Log",      "📋", False),
    ("Settings",       "⚙",  False),
]

STYLE = """
QMainWindow, QWidget { background:#0F1117; color:#E8EAF0; font-size:19px; }
QLabel { color:#E8EAF0; font-size:19px; }
#sidebar { background:#080A0F; border-right:1px solid #1E2130; }
#logo_label { color:#4080FF; font-size:29px; font-weight:bold;
              padding:20px; border-bottom:1px solid #1E2130; }
#sub_label  { color:#505870; font-size:16px; padding:0 20px 14px 20px; }
#card { background:#141824; border:1px solid #1E2130; border-radius:8px; padding:16px; }
#card_title { color:#8890A8; font-size:18px; font-weight:bold; letter-spacing:1px; }
#card_value { color:#FFFFFF; font-size:48px; font-weight:bold; }
#section_title { color:#FFFFFF; font-size:31px; font-weight:bold; }
#section_sub   { color:#505870; font-size:19px; }
#divider { background:#1E2130; max-height:1px; }
QPushButton#btn_primary {
    background:#4080FF; color:#FFF; border:none;
    padding:11px 24px; border-radius:6px; font-size:20px; font-weight:bold; }
QPushButton#btn_primary:hover { background:#5090FF; }
QPushButton#btn_success {
    background:#28A060; color:#FFF; border:none;
    padding:10px 20px; border-radius:6px; font-size:19px; font-weight:bold; }
QPushButton#btn_success:hover { background:#30B870; }
QPushButton#btn_danger {
    background:#C03030; color:#FFF; border:none;
    padding:10px 20px; border-radius:6px; font-size:19px; font-weight:bold; }
QPushButton#btn_danger:hover { background:#D04040; }
QPushButton#btn_warn {
    background:#C07010; color:#FFF; border:none;
    padding:10px 20px; border-radius:6px; font-size:19px; font-weight:bold; }
QPushButton#btn_warn:hover { background:#D08020; }
QPushButton#btn_sec {
    background:#1E2130; color:#C8D0E8; border:1px solid #2A3050;
    padding:10px 20px; border-radius:6px; font-size:19px; }
QPushButton#btn_sec:hover { background:#252A40; }
QTableWidget {
    background:#0F1117; border:1px solid #1E2130;
    gridline-color:#1A1E2A; color:#C8D0E8; font-size:18px;
    selection-background-color:#1A2040; }
QTableWidget::item { padding:8px 12px; border-bottom:1px solid #141824; }
QTableWidget::item:selected { background:#1A2040; color:#FFF; }
QHeaderView::section {
    background:#141824; color:#8890A8; padding:10px 12px;
    border:none; border-bottom:1px solid #1E2130;
    font-size:18px; font-weight:bold; letter-spacing:0.5px; }
QLineEdit, QComboBox, QTextEdit, QSpinBox {
    background:#141824; border:1px solid #2A3050;
    color:#E8EAF0; padding:10px 14px; border-radius:6px; font-size:19px; }
QLineEdit:focus, QComboBox:focus, QTextEdit:focus { border:1px solid #4080FF; }
QComboBox::drop-down { border:none; width:28px; }
QComboBox QAbstractItemView {
    background:#141824; color:#E8EAF0; font-size:19px;
    selection-background-color:#1A2040; border:1px solid #2A3050; }
QCheckBox { color:#C8D0E8; spacing:10px; font-size:19px; }
QCheckBox::indicator { width:20px; height:20px; border:1px solid #2A3050;
    border-radius:3px; background:#141824; }
QCheckBox::indicator:checked { background:#4080FF; border:1px solid #4080FF; }
QListWidget { background:#141824; border:1px solid #1E2130; color:#C8D0E8;
    font-size:19px; selection-background-color:#1A2040; }
QListWidget::item { padding:8px 12px; border-bottom:1px solid #1E2130; }
QScrollBar:vertical { background:#0F1117; width:8px; }
QScrollBar::handle:vertical { background:#2A3050; border-radius:4px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QTabWidget::pane { border:1px solid #1E2130; background:#0F1117; }
QTabBar::tab { background:#141824; color:#8890A8; padding:10px 22px;
    border:1px solid #1E2130; border-bottom:none; font-size:19px; }
QTabBar::tab:selected { background:#1A2040; color:#FFF; border-top:2px solid #4080FF; }
QProgressBar { background:#141824; border:none; border-radius:3px; height:5px; }
QProgressBar::chunk { background:#4080FF; border-radius:3px; }
QFormLayout QLabel { font-size:19px; min-width:160px; }
"""

# ── API ───────────────────────────────────────────────────────────────────────

def api(method, path, **kwargs):
    try:
        r = getattr(requests, method)(f"{API}{path}", timeout=10, **kwargs)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# ── SERVER THREAD ─────────────────────────────────────────────────────────────

class ServerThread(QThread):
    ready  = pyqtSignal()
    failed = pyqtSignal(str)
    def run(self):
        try:
            r = requests.get(f"{API}/ping", timeout=1)
            if r.status_code == 200: self.ready.emit(); return
        except: pass
        try:
            subprocess.Popen([sys.executable, str(SERVER_SCRIPT)],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for _ in range(20):
                time.sleep(0.5)
                try:
                    if requests.get(f"{API}/ping", timeout=1).status_code == 200:
                        self.ready.emit(); return
                except: pass
            self.failed.emit("Server did not start")
        except Exception as e:
            self.failed.emit(str(e))

# ── SHARED WIDGETS ────────────────────────────────────────────────────────────

class StatCard(QFrame):
    def __init__(self, title, value, sub, accent):
        super().__init__(); self.setObjectName("card")
        l = QVBoxLayout(self); l.setSpacing(4)
        t = QLabel(title.upper()); t.setObjectName("card_title")
        t.setFont(QFont("Segoe UI",12,QFont.Bold))
        self.vl = QLabel(str(value))
        self.vl.setFont(QFont("Segoe UI",35,QFont.Bold))
        self.vl.setStyleSheet(f"color:{accent};")
        s = QLabel(sub); s.setObjectName("card_sub")
        for w in [t, self.vl, s]: l.addWidget(w)
    def set_value(self, v): self.vl.setText(str(v))

def make_btn(label, style="sec"):
    b = QPushButton(label); b.setObjectName(f"btn_{style}"); return b

def page_header(title, sub=""):
    w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(0,0,0,8); l.setSpacing(2)
    t = QLabel(title); t.setObjectName("section_title")
    t.setFont(QFont("Segoe UI",25,QFont.Bold)); l.addWidget(t)
    if sub:
        s = QLabel(sub); s.setObjectName("section_sub"); l.addWidget(s)
    return w

def make_table(cols, stretch_col=None):
    t = QTableWidget(0, len(cols))
    t.setHorizontalHeaderLabels(cols)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.verticalHeader().setVisible(False)
    t.setAlternatingRowColors(False)
    if stretch_col is not None:
        t.horizontalHeader().setSectionResizeMode(stretch_col, QHeaderView.Stretch)
    return t

def tbl_item(text, color="#C8D0E8", bold=False):
    it = QTableWidgetItem(str(text))
    it.setForeground(QColor(color))
    if bold:
        f = it.font(); f.setBold(True); it.setFont(f)
    return it

# ── REVIEWER PICKER DIALOG ────────────────────────────────────────────────────

class ReviewerPickerDialog(QDialog):
    """Select reviewers and approver from roster, add notes, set due date."""
    def __init__(self, doc, mode="review", parent=None):
        super().__init__(parent)
        self.doc  = doc
        self.mode = mode
        self.setWindowTitle(f"{'Route for Review' if mode=='review' else 'Route for Approval'} — {doc['doc_id']}")
        self.setMinimumWidth(540)
        self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self); layout.setSpacing(12)

        layout.addWidget(page_header(
            f"{'Submit for Review' if mode=='review' else 'Submit for Approval'}",
            f"{doc['doc_id']} Rev {doc['version']} — {doc['title']}"
        ))

        # Load roster
        members = api("get", "/roster")
        if isinstance(members, dict): members = []
        self.members = members

        if mode == "review":
            layout.addWidget(QLabel("Select Reviewers:"))
            self.reviewer_checks = []
            scroll = QScrollArea(); scroll.setWidgetResizable(True)
            scroll.setMaximumHeight(180)
            inner = QWidget(); inner_l = QVBoxLayout(inner); inner_l.setSpacing(4)

            # Pre-check defaults
            defaults = api("get", "/roster/defaults",
                           params={"doc_type": doc["doc_id"].split("-")[0]})
            default_ids = {m["member_id"] for m in (defaults.get("reviewers") or [])}

            for m in [m for m in members if m.get("active") and m["role"] in
                      ("Reviewer","QA Lead","Approver","Author")]:
                cb = QCheckBox(f"{m['name']}  ({m['role']})  —  {m['email']}")
                cb.setProperty("member", m)
                if m["member_id"] in default_ids: cb.setChecked(True)
                self.reviewer_checks.append(cb)
                inner_l.addWidget(cb)
            if not self.reviewer_checks:
                inner_l.addWidget(QLabel("No team members found. Add them in Team Roster."))
            inner_l.addStretch()
            scroll.setWidget(inner)
            layout.addWidget(scroll)

            due_row = QHBoxLayout()
            due_row.addWidget(QLabel("Due in (days):"))
            self.due_spin = QSpinBox()
            self.due_spin.setRange(1, 90); self.due_spin.setValue(7)
            self.due_spin.setFixedWidth(80)
            due_row.addWidget(self.due_spin); due_row.addStretch()
            layout.addLayout(due_row)

        else:  # approval
            layout.addWidget(QLabel("Select Approver:"))
            self.approver_cb = QComboBox()
            approvers = [m for m in members if m.get("active")
                         and m["role"] in ("Approver","QA Lead")]
            for m in approvers:
                self.approver_cb.addItem(f"{m['name']}  ({m['role']})", m)
            if not approvers:
                self.approver_cb.addItem("No approvers configured")
            layout.addWidget(self.approver_cb)

        layout.addWidget(QLabel("Notes (optional):"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Add any context or instructions for the reviewer…")
        self.notes_edit.setMaximumHeight(80)
        layout.addWidget(self.notes_edit)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_lbl = "Send for Review" if mode == "review" else "Send for Approval"
        btns.button(QDialogButtonBox.Ok).setText(ok_lbl)
        btns.button(QDialogButtonBox.Ok).setStyleSheet(
            "background:#4080FF;color:#FFF;border:none;padding:8px 18px;"
            "border-radius:6px;font-weight:bold;")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_reviewers(self):
        return [cb.property("member") for cb in self.reviewer_checks if cb.isChecked()]

    def get_approver(self):
        if hasattr(self, "approver_cb"):
            return self.approver_cb.currentData()
        return None

    def get_notes(self): return self.notes_edit.toPlainText().strip()
    def get_due_days(self):
        return self.due_spin.value() if hasattr(self, "due_spin") else 7

# ── COMPLETE REVIEW DIALOG ────────────────────────────────────────────────────

class CompleteReviewDialog(QDialog):
    def __init__(self, route, parent=None):
        super().__init__(parent)
        self.route = route
        self.setWindowTitle(f"Complete Review — {route['doc_id']}")
        self.setMinimumWidth(460)
        self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self); layout.setSpacing(12)
        layout.addWidget(page_header("Complete Review",
            f"{route['doc_id']} — {route['doc_title']}"))
        layout.addWidget(QLabel("Reviewer Notes / Comments:"))
        self.notes = QTextEdit()
        self.notes.setPlaceholderText(
            "Summarize your review findings, any required changes, or confirm the document is ready.")
        self.notes.setMinimumHeight(100)
        layout.addWidget(self.notes)
        self.reject_cb = QCheckBox("Return to Author (document needs revision before approval)")
        self.reject_cb.setStyleSheet("color:#FF8080;")
        layout.addWidget(self.reject_cb)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("Submit Review")
        btns.button(QDialogButtonBox.Ok).setStyleSheet(
            "background:#28A060;color:#FFF;border:none;padding:8px 18px;"
            "border-radius:6px;font-weight:bold;")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
    def get_notes(self): return self.notes.toPlainText().strip()
    def is_rejected(self): return self.reject_cb.isChecked()

# ── PAGES ─────────────────────────────────────────────────────────────────────

class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        l = QVBoxLayout(self); l.setContentsMargins(28,24,28,24); l.setSpacing(20)
        l.addWidget(page_header("Dashboard","QMS system overview"))

        cards = QHBoxLayout(); cards.setSpacing(12)
        self.c_total    = StatCard("Total Docs",    "—","in register",          "#8890A8")
        self.c_draft    = StatCard("In Draft",       "—","being authored",        "#E8A020")
        self.c_review   = StatCard("In Review",      "—","awaiting sign-off",     "#4090FF")
        self.c_approved = StatCard("Approved",        "—","active & controlled",   "#30C070")
        self.c_pending  = StatCard("Pending Routes",  "—","awaiting action",       "#E8A020")
        self.c_notifs   = StatCard("Notifications",   "—","unread",               "#FF8080")
        for c in [self.c_total,self.c_draft,self.c_review,
                  self.c_approved,self.c_pending,self.c_notifs]:
            cards.addWidget(c)
        l.addLayout(cards)

        tabs = QTabWidget()
        # Recent activity
        act_w = QWidget(); act_l = QVBoxLayout(act_w); act_l.setContentsMargins(0,8,0,0)
        self.act_table = make_table(["Time","Action","Document","User"], stretch_col=2)
        act_l.addWidget(self.act_table)
        tabs.addTab(act_w, "Recent Activity")

        # Pending routing
        pnd_w = QWidget(); pnd_l = QVBoxLayout(pnd_w); pnd_l.setContentsMargins(0,8,0,0)
        self.pnd_table = make_table(
            ["Route ID","Document","Type","Assigned To","Due","Status"], stretch_col=1)
        pnd_l.addWidget(self.pnd_table)
        tabs.addTab(pnd_w, "Pending Routes")

        l.addWidget(tabs)

    def refresh(self):
        stats = api("get","/stats")
        self.c_total.set_value(stats.get("total","—"))
        self.c_draft.set_value(stats.get("DRAFT","—"))
        self.c_review.set_value(stats.get("IN_REVIEW","—"))
        self.c_approved.set_value(stats.get("APPROVED","—"))
        self.c_pending.set_value(
            (stats.get("pending_reviews",0) or 0) +
            (stats.get("pending_approvals",0) or 0))
        self.c_notifs.set_value(stats.get("unread_notifs","—"))

        log = api("get","/audit-log")
        self.act_table.setRowCount(0)
        for e in (log[:15] if isinstance(log,list) else []):
            r = self.act_table.rowCount(); self.act_table.insertRow(r)
            for col,val in enumerate([e.get("timestamp","")[:16].replace("T"," "),
                                      e.get("action",""),e.get("doc_id",""),e.get("user","")]):
                self.act_table.setItem(r,col,tbl_item(val))

        q = api("get","/routing/queue",params={"status":"PENDING"})
        self.pnd_table.setRowCount(0)
        for e in (q if isinstance(q,list) else []):
            r = self.pnd_table.rowCount(); self.pnd_table.insertRow(r)
            sc = ROUTE_STATUS_COLORS.get(e.get("status",""),"#888888")
            for col,val in enumerate([
                e.get("route_id",""),e.get("doc_id",""),
                e.get("route_type",""),e.get("assigned_to_name",""),
                e.get("due_date",""),e.get("status","")]):
                self.pnd_table.setItem(r,col,tbl_item(val,
                    sc if col==5 else "#C8D0E8", bold=(col==5)))


class DocumentsPage(QWidget):
    def __init__(self):
        super().__init__()
        l = QVBoxLayout(self); l.setContentsMargins(28,24,28,24); l.setSpacing(14)
        l.addWidget(page_header("Document Register"))

        fr = QHBoxLayout(); fr.setSpacing(10)
        self.search = QLineEdit(); self.search.setPlaceholderText("Search…")
        self.search.textChanged.connect(self.refresh); self.search.setMinimumWidth(220)
        self.sf = QComboBox()
        self.sf.addItems(["All Statuses","DRAFT","IN_REVIEW","APPROVED","OBSOLETE"])
        self.sf.currentTextChanged.connect(self.refresh)
        self.tf = QComboBox(); self.tf.addItems(["All Types"]+DOC_TYPES)
        self.tf.currentTextChanged.connect(self.refresh)
        rb = make_btn("↻ Refresh","sec"); rb.clicked.connect(self.refresh)
        for w in [self.search,self.sf,self.tf,rb]: fr.addWidget(w)
        l.addLayout(fr)

        self.table = make_table(["ID","Rev","Status","Title","Type","Owner","Route Status"],
                                stretch_col=3)
        self.table.doubleClicked.connect(self._open)
        l.addWidget(self.table)
        self.lbl = QLabel(""); self.lbl.setStyleSheet("color:#505870;font-size:14px;")
        l.addWidget(self.lbl)

    def refresh(self):
        params = {}
        s = self.sf.currentText(); t = self.tf.currentText(); q = self.search.text().strip()
        if s != "All Statuses": params["status"] = s
        if t != "All Types":    params["type"]   = t
        if q:                   params["search"] = q
        docs = api("get","/documents",params=params)
        if isinstance(docs,dict): docs = []

        # Get pending routes to show routing status per doc
        routes = api("get","/routing/queue",params={"status":"PENDING"})
        route_map = {}
        for rt in (routes if isinstance(routes,list) else []):
            did = rt.get("doc_id","")
            if did not in route_map: route_map[did] = []
            route_map[did].append(rt.get("route_type",""))

        self.table.setRowCount(0)
        for doc in docs:
            r = self.table.rowCount(); self.table.insertRow(r)
            sc  = STATUS_COLORS.get(doc.get("status",""),"#888888")
            did = doc.get("doc_id","")
            rt_label = ""
            if did in route_map:
                types = route_map[did]
                rt_label = "🔵 Review" if "REVIEW" in types else ""
                if "APPROVAL" in types: rt_label = "🟡 Approval"
            for col,(val,clr,bold) in enumerate([
                (did,"#4090FF",True),(doc.get("version",""),"#C8D0E8",False),
                (doc.get("status",""),sc,True),(doc.get("title",""),"#C8D0E8",False),
                (doc.get("type",""),"#C8D0E8",False),(doc.get("owner",""),"#C8D0E8",False),
                (rt_label,"#E8A020",False)
            ]):
                it = tbl_item(val,clr,bold)
                it.setData(Qt.UserRole, doc)
                self.table.setItem(r,col,it)
        self.lbl.setText(f"{len(docs)} document(s)")

    def _open(self, idx):
        it = self.table.item(idx.row(),0)
        if it:
            doc = it.data(Qt.UserRole)
            if doc: self._show_detail(doc)

    def _show_detail(self, doc):
        dlg = DocDetailDialog(doc, self)
        dlg.exec_()
        self.refresh()


class DocDetailDialog(QDialog):
    def __init__(self, doc, parent=None):
        super().__init__(parent)
        self.doc = doc
        self.setWindowTitle(f"{doc['doc_id']} — {doc['title']}")
        self.setMinimumWidth(600); self.setMinimumHeight(480)
        self.setStyleSheet(STYLE)
        l = QVBoxLayout(self); l.setSpacing(12)

        # Header
        h = QHBoxLayout()
        id_l = QLabel(doc["doc_id"]); id_l.setFont(QFont("Segoe UI",22,QFont.Bold))
        id_l.setStyleSheet("color:#4080FF;")
        sc = STATUS_COLORS.get(doc["status"],"#888")
        st = QLabel(doc["status"]); st.setStyleSheet(f"color:{sc};font-weight:bold;font-size:16px;")
        vl = QLabel(f"Rev {doc['version']}"); vl.setStyleSheet("color:#8890A8;font-size:16px;")
        h.addWidget(id_l); h.addWidget(st); h.addStretch(); h.addWidget(vl)
        l.addLayout(h)
        tl = QLabel(doc["title"]); tl.setFont(QFont("Segoe UI",15))
        tl.setStyleSheet("color:#C8D0E8;"); tl.setWordWrap(True); l.addWidget(tl)

        # Info grid
        g = QGridLayout(); g.setSpacing(6)
        fields = [("Type",doc.get("type","")),("Owner",doc.get("owner","")),
                  ("Created",doc.get("created_date","")),("Modified",doc.get("last_modified","")),
                  ("Approved By",doc.get("approved_by","—")),("Approved",doc.get("approved_date","—")),
                  ("Next Review",doc.get("next_review_date","—")),("Related",doc.get("related_docs","—")),
                  ("ISO 13485",doc.get("iso_13485_clause","—")),("ISO 9001",doc.get("iso_9001_clause","—")),
                  ("ISO 14971",doc.get("iso_14971_clause","—"))]
        for i,(k,v) in enumerate(fields):
            row,col = divmod(i,2)
            kl = QLabel(k+":"); kl.setStyleSheet("color:#505870;font-size:14px;font-weight:bold;")
            vl2 = QLabel(v or "—"); vl2.setStyleSheet("color:#C8D0E8;font-size:15px;")
            vl2.setWordWrap(True)
            g.addWidget(kl,row,col*2); g.addWidget(vl2,row,col*2+1)
        l.addLayout(g)

        div = QFrame(); div.setObjectName("divider"); div.setFixedHeight(1); l.addWidget(div)

        # Route status
        routes = api("get","/routing/queue",params={"doc_id":doc["doc_id"],"status":"PENDING"})
        if isinstance(routes,list) and routes:
            rl = QLabel(f"⚡ Active routes: {len(routes)} pending")
            rl.setStyleSheet("color:#E8A020;font-size:15px;font-weight:bold;")
            l.addWidget(rl)

        # Actions
        br = QHBoxLayout(); br.setSpacing(8)

        ob = make_btn("Open Document","primary")
        ob.clicked.connect(lambda: api("post",f"/documents/{doc['doc_id']}/open",json={"type":"docx"}))
        if doc.get("pdf_path"):
            pb = make_btn("View PDF","sec")
            pb.clicked.connect(lambda: api("post",f"/documents/{doc['doc_id']}/open",json={"type":"pdf"}))
            br.addWidget(pb)

        if doc["status"] == "DRAFT":
            rv = make_btn("→ Route for Review","primary")
            rv.clicked.connect(lambda: self._route_review())
            br.addWidget(rv)
        elif doc["status"] == "IN_REVIEW":
            ap = make_btn("→ Route for Approval","warn")
            ap.clicked.connect(lambda: self._route_approval())
            br.addWidget(ap)
            app_btn = make_btn("✓ Approve","success")
            app_btn.clicked.connect(lambda: self._approve())
            br.addWidget(app_btn)
        elif doc["status"] == "APPROVED":
            obs = make_btn("Archive","danger")
            obs.clicked.connect(lambda: self._obsolete())
            br.addWidget(obs)

        br.addWidget(ob); br.addStretch()
        cl = make_btn("Close","sec"); cl.clicked.connect(self.accept); br.addWidget(cl)
        l.addLayout(br)

    def _route_review(self):
        dlg = ReviewerPickerDialog(self.doc, "review", self)
        if dlg.exec_() == QDialog.Accepted:
            reviewers = dlg.get_reviewers()
            if not reviewers:
                QMessageBox.warning(self,"QMS","No reviewers selected."); return
            cfg = api("get","/config")
            result = api("post","/routing/submit-review", json={
                "doc_id":     self.doc["doc_id"],
                "reviewers":  reviewers,
                "sender_name":cfg.get("current_user",""),
                "sender_email":cfg.get("current_email",""),
                "notes":      dlg.get_notes(),
                "due_days":   dlg.get_due_days()
            })
            if result.get("ok"):
                QMessageBox.information(self,"Routed",
                    f"{self.doc['doc_id']} routed to {len(reviewers)} reviewer(s).\n"
                    f"Notifications queued.")
                self.accept()
            else:
                QMessageBox.warning(self,"Error",result.get("error","Unknown error"))

    def _route_approval(self):
        dlg = ReviewerPickerDialog(self.doc, "approval", self)
        if dlg.exec_() == QDialog.Accepted:
            approver = dlg.get_approver()
            if not approver:
                QMessageBox.warning(self,"QMS","No approver selected."); return
            cfg = api("get","/config")
            result = api("post","/routing/submit-approval", json={
                "doc_id":     self.doc["doc_id"],
                "approver":   approver,
                "sender_name":cfg.get("current_user",""),
                "notes":      dlg.get_notes()
            })
            if result.get("ok"):
                QMessageBox.information(self,"Routed",
                    f"{self.doc['doc_id']} routed to {approver['name']} for approval.")
                self.accept()
            else:
                QMessageBox.warning(self,"Error",result.get("error","Unknown error"))

    def _approve(self):
        cfg = api("get","/config")
        user = cfg.get("current_user","QA User")
        if QMessageBox.question(self,"Confirm Approval",
            f"Approve {self.doc['doc_id']}?\n\nApprover: {user}\n"
            "This will generate a stamped PDF.",
            QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            result = api("post",f"/documents/{self.doc['doc_id']}/promote",
                         json={"to":"approved","user":user})
            if result.get("ok"):
                QMessageBox.information(self,"Approved",
                    f"{self.doc['doc_id']} Rev{result.get('version','')} approved.")
                self.accept()
            else:
                QMessageBox.warning(self,"Error",result.get("error",""))

    def _obsolete(self):
        if QMessageBox.question(self,"Archive",
            f"Archive {self.doc['doc_id']} as OBSOLETE?",
            QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            cfg = api("get","/config")
            api("post",f"/documents/{self.doc['doc_id']}/obsolete",
                json={"user":cfg.get("current_user","QA User")})
            self.accept()



class ImportDialog(QDialog):
    """Dialog for importing an existing file into the DMS."""
    def __init__(self, fpath, parent=None):
        super().__init__(parent)
        self.fpath = fpath
        self.setWindowTitle("Import Existing File")
        self.setMinimumWidth(520)
        l = QVBoxLayout(self); l.setSpacing(12)

        # Header showing file being imported
        from pathlib import Path
        fname_lbl = QLabel(f"Importing: {Path(fpath).name}")
        fname_lbl.setStyleSheet("color:#4080FF;font-size:15px;font-weight:bold;")
        fname_lbl.setWordWrap(True)
        l.addWidget(fname_lbl)

        card = QFrame(); card.setObjectName("card")
        fl = QFormLayout(card); fl.setSpacing(10); fl.setContentsMargins(16,16,16,16)

        cfg = api("get","/config")
        formal   = list((cfg.get("prefix_scheme") or {}).keys()) or DOC_TYPES
        informal = list((cfg.get("informal_prefix_scheme") or {}).keys())

        self.type_cb = QComboBox()
        self.type_cb.addItems(formal + informal)
        self.type_cb.setCurrentText("SOP")

        self.cat_cb = QComboBox()
        self.cat_cb.addItems(["FORMAL (Full QMS)", "NOT UNDER QMS (Informal)"])

        self.proj_cb = QComboBox()
        projects = cfg.get("projects", {})
        self.proj_cb.addItem("None (QMS-level / shared)", "")
        for code, name in (projects or {}).items():
            self.proj_cb.addItem(f"{code}  —  {name}", code)

        self.title_edit = QLineEdit()
        self.title_edit.setText(Path(fpath).stem.replace("_"," ").replace("-"," "))
        self.owner_edit = QLineEdit()
        self.owner_edit.setText(cfg.get("current_user","QA User"))

        self.ver_edit   = QLineEdit(); self.ver_edit.setPlaceholderText("A for draft, 1 for approved")
        self.ver_edit.setText("A")

        self.status_cb  = QComboBox()
        self.status_cb.addItems(["DRAFT","IN_REVIEW","APPROVED_PENDING","EFFECTIVE","APPROVED"])

        self.cr_edit    = QLineEdit(); self.cr_edit.setPlaceholderText("CR-0001 (optional)")

        self.copy_cb    = QCheckBox("Keep original file in place (copy, don't move)")
        self.copy_cb.setChecked(False)

        fl.addRow("Document Type:",  self.type_cb)
        fl.addRow("Category:",       self.cat_cb)
        fl.addRow("Project:",        self.proj_cb)
        fl.addRow("Title *:",        self.title_edit)
        fl.addRow("Owner *:",        self.owner_edit)
        fl.addRow("Current Version:",self.ver_edit)
        fl.addRow("Current Status:", self.status_cb)
        fl.addRow("CR Number:",      self.cr_edit)
        fl.addRow("",                self.copy_cb)
        l.addWidget(card)

        warn = QLabel("⚠ The file will be moved to the appropriate QMS folder and renamed to match the naming convention. Check 'Keep original' to copy instead.")
        warn.setWordWrap(True); warn.setStyleSheet("color:#E8A020;font-size:13px;")
        l.addWidget(warn)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("Import Document")
        btns.button(QDialogButtonBox.Ok).setStyleSheet(
            "background:#2A6A2A;color:#FFF;border:none;padding:8px 18px;"
            "border-radius:6px;font-weight:bold;font-size:15px;")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        l.addWidget(btns)

    def get_data(self):
        cat_map = {"FORMAL (Full QMS)": "FORMAL",
                   "NOT UNDER QMS (Informal)": "NOT UNDER QMS"}
        return {
            "source_path": self.fpath,
            "type":        self.type_cb.currentText(),
            "doc_category":cat_map.get(self.cat_cb.currentText(), "FORMAL"),
            "project_code":self.proj_cb.currentData() or "",
            "title":       self.title_edit.text().strip(),
            "owner":       self.owner_edit.text().strip(),
            "version":     self.ver_edit.text().strip() or "A",
            "status":      self.status_cb.currentText(),
            "cr_id":       self.cr_edit.text().strip(),
            "copy_only":   self.copy_cb.isChecked(),
        }

class NewDocPage(QWidget):
    def __init__(self, on_created=None):
        super().__init__(); self.on_created = on_created
        l = QVBoxLayout(self); l.setContentsMargins(28,24,280,24); l.setSpacing(14)
        l.addWidget(page_header("Create New Document",
                                "Register and scaffold a new controlled document"))
        card = QFrame(); card.setObjectName("card")
        fl = QFormLayout(card); fl.setSpacing(12); fl.setContentsMargins(20,20,20,20)
        self.tc = QComboBox()
        cfg = api("get","/config")
        # Build type list from config prefix schemes
        formal   = list((cfg.get("prefix_scheme") or {}).keys()) or DOC_TYPES
        informal = list((cfg.get("informal_prefix_scheme") or {}).keys())
        all_types = formal + (["---INFORMAL---"] + informal if informal else [])
        self.tc.addItems(all_types)
        self.tc.setCurrentText("SOP")

        # Document category toggle
        self.cat_formal   = QCheckBox("Formal (Full QMS)")
        self.cat_informal = QCheckBox("Informal (Not Under QMS)")
        self.cat_formal.setChecked(True)
        self.cat_formal.stateChanged.connect(lambda s: self.cat_informal.setChecked(not s))
        self.cat_informal.stateChanged.connect(lambda s: self.cat_formal.setChecked(not s))
        cat_row = QHBoxLayout(); cat_row.addWidget(self.cat_formal)
        cat_row.addWidget(self.cat_informal); cat_row.addStretch()

        # Project selector
        self.proj_cb = QComboBox()
        projects = cfg.get("projects", {})
        self.proj_cb.addItem("None (QMS-level / shared)", "")
        for code, name in (projects or {}).items():
            self.proj_cb.addItem(f"{code}  —  {name}", code)

        self.ti = QLineEdit(); self.ti.setPlaceholderText("Full document title")
        self.ow = QLineEdit(); self.ow.setText(cfg.get("current_user","QA User"))
        self.c13 = QLineEdit(); self.c13.setPlaceholderText("e.g. 7.3")
        self.c9  = QLineEdit(); self.c9.setPlaceholderText("e.g. 8.3")
        self.c14 = QLineEdit(); self.c14.setPlaceholderText("e.g. 4, 5, 6")
        self.rel = QLineEdit(); self.rel.setPlaceholderText("e.g. SOP-001, QM-001")
        self.cr_field = QLineEdit(); self.cr_field.setPlaceholderText("e.g. CR-0001 (optional)")
        self.auto_route = QCheckBox("Automatically route for review after creation")
        self.auto_route.setChecked(False)

        fl.addRow("Document Type:", self.tc)
        fl.addRow("", cat_row)
        fl.addRow("Project:", self.proj_cb)
        fl.addRow("Title *:", self.ti)
        fl.addRow("Owner *:", self.ow)
        fl.addRow("ISO 13485:", self.c13)
        fl.addRow("ISO 9001:", self.c9)
        fl.addRow("ISO 14971:", self.c14)
        fl.addRow("Related Docs:", self.rel)
        fl.addRow("CR Number:", self.cr_field)
        fl.addRow("", self.auto_route)
        l.addWidget(card)
        self.rl = QLabel(""); self.rl.setWordWrap(True)
        self.rl.setStyleSheet("color:#30C070;font-size:16px;padding:6px 0;")
        l.addWidget(self.rl)
        br = QHBoxLayout(); br.setSpacing(10)
        cb = make_btn("Create Document","primary")
        cb.setStyleSheet("background:#4080FF;color:#FFF;border:none;padding:10px 24px;"
                         "border-radius:6px;font-size:18px;font-weight:bold;")
        cb.clicked.connect(self._create)
        ib = make_btn("Import Existing File","sec")
        ib.setStyleSheet("background:#2A4A2A;color:#90D090;border:1px solid #3A6A3A;"
                         "padding:10px 20px;border-radius:6px;font-size:15px;font-weight:bold;")
        ib.clicked.connect(self._import)
        cl = make_btn("Clear","sec"); cl.clicked.connect(self._clear)
        br.addWidget(cb); br.addWidget(ib); br.addWidget(cl); br.addStretch()
        l.addLayout(br); l.addStretch()

    def _create(self):
        title = self.ti.text().strip()
        if not title:
            self.rl.setStyleSheet("color:#FF5050;font-size:16px;")
            self.rl.setText("⚠ Title is required."); return
        proj_code = self.proj_cb.currentData() or ""
        category  = "FORMAL" if self.cat_formal.isChecked() else "NOT UNDER QMS"
        dtype = self.tc.currentText()
        if dtype == "---INFORMAL---":
            self.rl.setStyleSheet("color:#FF5050;font-size:15px;")
            self.rl.setText("⚠ Select a specific document type, not the separator."); return
        data = {"type": dtype, "title": title,
                "owner": self.ow.text().strip() or "QA User",
                "clause_13485": self.c13.text().strip(),
                "clause_9001":  self.c9.text().strip(),
                "clause_14971": self.c14.text().strip(),
                "related":      self.rel.text().strip(),
                "cr_id":        self.cr_field.text().strip(),
                "doc_category": category,
                "project_code": proj_code}
        result = api("post","/documents/new",json=data)
        if result.get("ok"):
            self.rl.setStyleSheet("color:#30C070;font-size:16px;")
            self.rl.setText(f"✓ Created {result['doc_id']} — template generated in Draft folder.")
            if self.auto_route.isChecked():
                # Fetch the doc and open routing dialog
                doc = api("get",f"/documents/{result['doc_id']}")
                if not doc.get("error"):
                    dlg = ReviewerPickerDialog(doc,"review",self)
                    if dlg.exec_() == QDialog.Accepted:
                        reviewers = dlg.get_reviewers()
                        if reviewers:
                            cfg = api("get","/config")
                            api("post","/routing/submit-review",json={
                                "doc_id":result["doc_id"],"reviewers":reviewers,
                                "sender_name":cfg.get("current_user",""),
                                "notes":dlg.get_notes(),"due_days":dlg.get_due_days()})
            self._clear()
            if self.on_created: self.on_created()
        else:
            self.rl.setStyleSheet("color:#FF5050;font-size:16px;")
            self.rl.setText(f"⚠ {result.get('error','Unknown error')}")

    def _clear(self):
        self.ti.clear(); self.c13.clear(); self.c9.clear()
        self.c14.clear(); self.rel.clear(); self.cr_field.clear()
        self.proj_cb.setCurrentIndex(0); self.cat_formal.setChecked(True)

    def _import(self):
        """Import an existing file into the DMS."""
        fpath, _ = QFileDialog.getOpenFileName(
            self, "Select File to Import", "",
            "Documents (*.docx *.xlsx *.pdf *.doc *.xls);;All Files (*)")
        if not fpath:
            return

        dlg = ImportDialog(fpath, self)
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.get_data()
            result = api("post", "/documents/import", json=data)
            if result.get("ok"):
                self.rl.setStyleSheet("color:#30C070;font-size:15px;")
                self.rl.setText(
                    f"✓ Imported as {result['doc_id']} — "
                    f"file registered in {data.get('status','DRAFT')} folder.")
                if self.on_created: self.on_created()
            else:
                self.rl.setStyleSheet("color:#FF5050;font-size:15px;")
                self.rl.setText(f"⚠ Import failed: {result.get('error','Unknown error')}")


class RoutingPage(QWidget):
    def __init__(self):
        super().__init__()
        l = QVBoxLayout(self); l.setContentsMargins(28,24,28,24); l.setSpacing(14)
        l.addWidget(page_header("Document Routing","Review and approval queue"))

        tabs = QTabWidget()

        # ── Pending tab ──
        pnd_w = QWidget(); pnd_l = QVBoxLayout(pnd_w); pnd_l.setContentsMargins(0,8,0,0)
        ctrl = QHBoxLayout()
        self.u_filter = QLineEdit(); self.u_filter.setPlaceholderText("Filter by person…")
        self.u_filter.textChanged.connect(self.refresh); self.u_filter.setMaximumWidth(220)
        self.rt_filter = QComboBox()
        self.rt_filter.addItems(["All Types","REVIEW","APPROVAL","FYI"])
        self.rt_filter.currentTextChanged.connect(self.refresh)
        rb = make_btn("↻ Refresh","sec"); rb.clicked.connect(self.refresh)
        ctrl.addWidget(self.u_filter); ctrl.addWidget(self.rt_filter)
        ctrl.addWidget(rb); ctrl.addStretch()
        pnd_l.addLayout(ctrl)
        self.pnd_table = make_table(
            ["Route ID","Document","Title","Type","Assigned To","Due","Status","Action"],
            stretch_col=2)
        self.pnd_table.setColumnWidth(7, 120)
        self.pnd_table.doubleClicked.connect(self._pnd_action)
        pnd_l.addWidget(self.pnd_table)
        tabs.addTab(pnd_w,"Pending")

        # ── All Routes tab ──
        all_w = QWidget(); all_l = QVBoxLayout(all_w); all_l.setContentsMargins(0,8,0,0)
        self.all_table = make_table(
            ["Route ID","Document","Type","Assigned To","By","Created","Due","Status"],
            stretch_col=1)
        all_l.addWidget(self.all_table)
        tabs.addTab(all_w,"All Routes")

        l.addWidget(tabs)
        self.tabs = tabs

    def refresh(self):
        # Pending
        params = {"status":"PENDING"}
        uf = self.u_filter.text().strip()
        rf = self.rt_filter.currentText()
        if uf: params["user"] = uf
        q = api("get","/routing/queue",params=params)
        if isinstance(q,dict): q = []
        if rf != "All Types": q = [r for r in q if r.get("route_type")==rf]

        self.pnd_table.setRowCount(0)
        cfg = api("get","/config")
        me  = cfg.get("current_user","").lower()

        for entry in q:
            r = self.pnd_table.rowCount(); self.pnd_table.insertRow(r)
            sc = ROUTE_STATUS_COLORS.get(entry.get("status",""),"#888")
            is_mine = entry.get("assigned_to_name","").lower() == me
            for col,(val,clr,bold) in enumerate([
                (entry.get("route_id",""),"#505870",False),
                (entry.get("doc_id",""),"#4090FF",True),
                (entry.get("doc_title",""),"#C8D0E8",False),
                (entry.get("route_type",""),"#8890A8",False),
                (entry.get("assigned_to_name",""),
                 "#FFFFFF" if is_mine else "#C8D0E8", is_mine),
                (entry.get("due_date",""),"#C8D0E8",False),
                (entry.get("status",""),sc,True),
                ("★ Action" if is_mine else "View","#4080FF" if is_mine else "#505870",is_mine)
            ]):
                it = tbl_item(val,clr,bold)
                it.setData(Qt.UserRole,entry)
                self.pnd_table.setItem(r,col,it)

        # All routes
        all_q = api("get","/routing/queue")
        if isinstance(all_q,dict): all_q = []
        self.all_table.setRowCount(0)
        for entry in all_q:
            r = self.all_table.rowCount(); self.all_table.insertRow(r)
            sc = ROUTE_STATUS_COLORS.get(entry.get("status",""),"#888")
            for col,val in enumerate([
                entry.get("route_id",""),entry.get("doc_id",""),
                entry.get("route_type",""),entry.get("assigned_to_name",""),
                entry.get("assigned_by_name",""),entry.get("created_date",""),
                entry.get("due_date",""),entry.get("status","")]):
                clr = sc if col==7 else "#C8D0E8"
                self.all_table.setItem(r,col,tbl_item(val,clr,bold=(col==7)))

    def _pnd_action(self, idx):
        it = self.pnd_table.item(idx.row(),0)
        if not it: return
        entry = it.data(Qt.UserRole)
        if not entry: return
        cfg = api("get","/config")
        me  = cfg.get("current_user","").lower()
        is_mine = entry.get("assigned_to_name","").lower() == me

        if is_mine and entry.get("route_type") == "REVIEW":
            dlg = CompleteReviewDialog(entry, self)
            if dlg.exec_() == QDialog.Accepted:
                result = api("post","/routing/complete-review",json={
                    "route_id":  entry["route_id"],
                    "doc_id":    entry["doc_id"],
                    "reviewer_name": cfg.get("current_user",""),
                    "notes":     dlg.get_notes(),
                    "rejected":  dlg.is_rejected()
                })
                if result.get("ok"):
                    QMessageBox.information(self,"Done",
                        "Review submitted." + (" Document returned to author." if dlg.is_rejected() else ""))
                    self.refresh()
        elif is_mine and entry.get("route_type") == "APPROVAL":
            doc = api("get",f"/documents/{entry['doc_id']}")
            if not doc.get("error"):
                dd = DocDetailDialog(doc, self); dd.exec_(); self.refresh()
        else:
            # Show route info
            msg = (f"Route: {entry['route_id']}\n"
                   f"Document: {entry['doc_id']} — {entry['doc_title']}\n"
                   f"Type: {entry['route_type']}\n"
                   f"Assigned to: {entry['assigned_to_name']}\n"
                   f"By: {entry['assigned_by_name']}\n"
                   f"Due: {entry['due_date']}\n"
                   f"Notes: {entry.get('notes_from_sender','')}")
            QMessageBox.information(self,"Route Details",msg)


class NotificationsPage(QWidget):
    def __init__(self):
        super().__init__()
        l = QVBoxLayout(self); l.setContentsMargins(28,24,28,24); l.setSpacing(14)

        hdr = QHBoxLayout()
        hdr.addWidget(page_header("Notifications","Your pending alerts and messages"))
        hdr.addStretch()
        da = make_btn("Dismiss All","sec")
        da.clicked.connect(self._dismiss_all)
        hdr.addWidget(da)
        l.addLayout(hdr)

        self.inc_dismissed = QCheckBox("Show dismissed")
        self.inc_dismissed.stateChanged.connect(self.refresh)
        l.addWidget(self.inc_dismissed)

        self.table = make_table(
            ["Type","Document","Subject","From","Date","Status"], stretch_col=2)
        self.table.doubleClicked.connect(self._open_notif)
        l.addWidget(self.table)
        self.lbl = QLabel(""); self.lbl.setStyleSheet("color:#505870;font-size:14px;")
        l.addWidget(self.lbl)

    def refresh(self):
        cfg  = api("get","/config")
        inc  = self.inc_dismissed.isChecked()
        data = api("get","/notifications",params={
            "user":  cfg.get("current_user",""),
            "email": cfg.get("current_email",""),
            "include_dismissed": "true" if inc else "false"
        })
        if isinstance(data,dict): data = []
        self.table.setRowCount(0)
        unread = 0
        for n in data:
            r = self.table.rowCount(); self.table.insertRow(r)
            nt   = n.get("notification_type","")
            nc   = NOTIF_COLORS.get(nt,"#8890A8")
            dim  = n.get("dismissed",False)
            alpha = "#555555" if dim else "#C8D0E8"
            if not dim: unread += 1
            for col,(val,clr) in enumerate([
                (nt,nc),(n.get("doc_id",""),("#4090FF" if not dim else "#334455")),
                (n.get("subject",""),alpha),(n.get("recipient_name",""),alpha),
                (n.get("created_date","")[:16].replace("T"," "),alpha),
                ("Read" if dim else "Unread","#555555" if dim else "#30C070")
            ]):
                it = tbl_item(val,clr,bold=(col==0 and not dim))
                it.setData(Qt.UserRole,n)
                self.table.setItem(r,col,it)
        self.lbl.setText(f"{len(data)} notification(s) — {unread} unread")

    def _open_notif(self, idx):
        it = self.table.item(idx.row(),0)
        if not it: return
        n = it.data(Qt.UserRole)
        if not n: return
        QMessageBox.information(self, n.get("subject","Notification"), n.get("body",""))
        api("post","/notifications/dismiss",json={"notif_id":n["notif_id"]})
        self.refresh()

    def _dismiss_all(self):
        cfg = api("get","/config")
        api("post","/notifications/dismiss-all",json={"user":cfg.get("current_user","")})
        self.refresh()


class TeamRosterPage(QWidget):
    def __init__(self):
        super().__init__()
        l = QVBoxLayout(self); l.setContentsMargins(28,24,28,24); l.setSpacing(14)
        l.addWidget(page_header("Team Roster",
            "Manage who receives review requests and approvals"))

        tabs = QTabWidget()

        # ── Members tab ──
        mem_w = QWidget(); mem_l = QVBoxLayout(mem_w); mem_l.setContentsMargins(0,8,0,0)
        ctrl = QHBoxLayout()
        ab = make_btn("+ Add Member","primary")
        ab.setStyleSheet("background:#4080FF;color:#FFF;border:none;padding:8px 16px;"
                         "border-radius:6px;font-weight:bold;")
        ab.clicked.connect(self._add_member)
        ctrl.addWidget(ab); ctrl.addStretch()
        mem_l.addLayout(ctrl)
        self.mem_table = make_table(
            ["Name","Email","Role","Doc Types","Active","Added"], stretch_col=0)
        self.mem_table.doubleClicked.connect(self._edit_member)
        mem_l.addWidget(self.mem_table)
        tabs.addTab(mem_w,"Members")

        # ── Add/Edit form tab ──
        form_w = QWidget(); form_l = QVBoxLayout(form_w)
        form_l.setContentsMargins(0,12,0,0); form_l.setSpacing(12)
        card = QFrame(); card.setObjectName("card")
        fl = QFormLayout(card); fl.setSpacing(10); fl.setContentsMargins(16,16,16,16)
        self.nm = QLineEdit(); self.nm.setPlaceholderText("Full name")
        self.em = QLineEdit(); self.em.setPlaceholderText("email@company.com")
        self.rl = QComboBox(); self.rl.addItems(ROLES)
        # Doc types checkboxes
        dt_w = QWidget(); dt_l = QHBoxLayout(dt_w); dt_l.setContentsMargins(0,0,0,0)
        dt_l.setSpacing(6)
        self.dt_checks = {}
        all_cb = QCheckBox("ALL")
        all_cb.setProperty("dtype","ALL")
        self.dt_checks["ALL"] = all_cb
        dt_l.addWidget(all_cb)
        for dt in DOC_TYPES:
            cb = QCheckBox(dt); cb.setProperty("dtype",dt)
            self.dt_checks[dt] = cb; dt_l.addWidget(cb)
        fl.addRow("Name *:", self.nm); fl.addRow("Email *:", self.em)
        fl.addRow("Role:", self.rl); fl.addRow("Default Doc Types:", dt_w)
        form_l.addWidget(card)
        br = QHBoxLayout()
        sb = make_btn("Save Member","primary")
        sb.setStyleSheet("background:#4080FF;color:#FFF;border:none;padding:9px 20px;"
                         "border-radius:6px;font-weight:bold;")
        sb.clicked.connect(self._save_member)
        clr = make_btn("Clear","sec"); clr.clicked.connect(self._clear_form)
        br.addWidget(sb); br.addWidget(clr); br.addStretch()
        form_l.addLayout(br)
        self.form_result = QLabel("")
        self.form_result.setStyleSheet("color:#30C070;font-size:15px;")
        form_l.addWidget(self.form_result); form_l.addStretch()
        tabs.addTab(form_w,"Add / Edit Member")

        l.addWidget(tabs); self.tabs = tabs
        self._edit_id = None

    def refresh(self):
        members = api("get","/roster")
        if isinstance(members,dict): members = []
        self.mem_table.setRowCount(0)
        for m in members:
            r = self.mem_table.rowCount(); self.mem_table.insertRow(r)
            ac = "#30C070" if m.get("active") else "#888888"
            for col,(val,clr) in enumerate([
                (m.get("name",""),"#FFFFFF"),
                (m.get("email",""),"#8890A8"),
                (m.get("role",""),"#C8D0E8"),
                (", ".join(m.get("doc_types",[])),"#C8D0E8"),
                ("Yes" if m.get("active") else "No", ac),
                (m.get("added_date",""),"#505870")
            ]):
                it = tbl_item(val,clr,bold=(col==0))
                it.setData(Qt.UserRole,m)
                self.mem_table.setItem(r,col,it)

    def _add_member(self):
        self._edit_id = None; self._clear_form()
        self.tabs.setCurrentIndex(1)

    def _edit_member(self, idx):
        it = self.mem_table.item(idx.row(),0)
        if not it: return
        m = it.data(Qt.UserRole)
        if not m: return
        self._edit_id = m["member_id"]
        self.nm.setText(m.get("name","")); self.em.setText(m.get("email",""))
        self.rl.setCurrentText(m.get("role","Reviewer"))
        dts = m.get("doc_types",[])
        for k,cb in self.dt_checks.items(): cb.setChecked(k in dts)
        self.tabs.setCurrentIndex(1)

    def _save_member(self):
        name = self.nm.text().strip(); email = self.em.text().strip()
        if not name or not email:
            self.form_result.setStyleSheet("color:#FF5050;font-size:15px;")
            self.form_result.setText("⚠ Name and email are required."); return
        dts = [k for k,cb in self.dt_checks.items() if cb.isChecked()]
        if self._edit_id:
            result = api("post","/roster/update",json={
                "member_id":self._edit_id,
                "updates":{"name":name,"email":email,
                           "role":self.rl.currentText(),"doc_types":dts}})
        else:
            result = api("post","/roster/add",json={
                "name":name,"email":email,
                "role":self.rl.currentText(),"doc_types":dts})
        if result.get("ok"):
            self.form_result.setStyleSheet("color:#30C070;font-size:15px;")
            self.form_result.setText("✓ Saved.")
            self._clear_form(); self.refresh(); self.tabs.setCurrentIndex(0)
        else:
            self.form_result.setStyleSheet("color:#FF5050;font-size:15px;")
            self.form_result.setText(f"⚠ {result.get('error','Error')}")

    def _clear_form(self):
        self.nm.clear(); self.em.clear(); self.rl.setCurrentIndex(0)
        for cb in self.dt_checks.values(): cb.setChecked(False)
        self.form_result.setText(""); self._edit_id = None


class ReviewDuePage(QWidget):
    def __init__(self):
        super().__init__()
        l = QVBoxLayout(self); l.setContentsMargins(28,24,28,24); l.setSpacing(14)
        l.addWidget(page_header("Periodic Review Due","Annual review tracking"))
        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("Show due within:"))
        self.dc = QComboBox(); self.dc.addItems(["30 days","60 days","90 days","180 days"])
        self.dc.setCurrentIndex(1); self.dc.currentIndexChanged.connect(self.refresh)
        ctrl.addWidget(self.dc); ctrl.addStretch()
        l.addLayout(ctrl)
        self.table = make_table(["ID","Rev","Title","Owner","Due Date","Days Left"],
                                stretch_col=2)
        l.addWidget(self.table)
        self.nl = QLabel(""); l.addWidget(self.nl)

    def refresh(self):
        days = int(self.dc.currentText().split()[0])
        docs = api("get","/review-due",params={"days":days})
        if isinstance(docs,dict): docs = []
        self.table.setRowCount(0)
        today = date.today()
        for doc in docs:
            r = self.table.rowCount(); self.table.insertRow(r)
            due = doc.get("next_review_date","")
            try:
                dl  = (date.fromisoformat(due)-today).days
                dlc = "#FF5050" if dl<15 else "#E8A020" if dl<45 else "#C8D0E8"
            except: dl = 0; dlc = "#888"; due = "—"
            for col,(val,clr,bold) in enumerate([
                (doc.get("doc_id",""),"#4090FF",True),(doc.get("version",""),"#C8D0E8",False),
                (doc.get("title",""),"#C8D0E8",False),(doc.get("owner",""),"#C8D0E8",False),
                (due,"#C8D0E8",False),(str(dl)+" days",dlc,True)
            ]):
                self.table.setItem(r,col,tbl_item(val,clr,bold))
        self.nl.setText("" if docs else "✓ No documents due in this window.")
        self.nl.setStyleSheet("color:#30C070;font-size:16px;" if not docs else "")


class AuditLogPage(QWidget):
    def __init__(self):
        super().__init__()
        l = QVBoxLayout(self); l.setContentsMargins(28,24,28,24); l.setSpacing(14)
        l.addWidget(page_header("Audit Log","Complete system action history"))
        self.table = make_table(["Timestamp","Action","Document","User","Details"],
                                stretch_col=4)
        l.addWidget(self.table)

    def refresh(self):
        log = api("get","/audit-log")
        if isinstance(log,dict): log = []
        ac = {"NEW":"#4090FF","APPROVE":"#30C070","PROMOTE_TO_REVIEW":"#E8A020",
              "OBSOLETE":"#888888","ROUTE_FOR_REVIEW":"#4090FF",
              "ROUTE_FOR_APPROVAL":"#E8A020","REVIEW_COMPLETE":"#30C070",
              "REVIEW_REJECTED":"#FF5050","RECALL":"#888888"}
        self.table.setRowCount(0)
        for e in log[:150]:
            r = self.table.rowCount(); self.table.insertRow(r)
            a = e.get("action","")
            for col,(val,clr) in enumerate([
                (e.get("timestamp","")[:19].replace("T"," "),"#C8D0E8"),
                (a, ac.get(a,"#C8D0E8")),
                (e.get("doc_id",""),"#4090FF"),
                (e.get("user",""),"#C8D0E8"),
                (e.get("details",""),"#505870")
            ]):
                self.table.setItem(r,col,tbl_item(val,clr,bold=(col==1)))


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        l = QVBoxLayout(self); l.setContentsMargins(28,24,28,24); l.setSpacing(14)
        l.addWidget(page_header("Settings", "System configuration and client customization"))

        tabs = QTabWidget()

        # ── Tab 1: General ──────────────────────────────────────────────────
        gen_w = QWidget(); gen_l = QVBoxLayout(gen_w)
        gen_l.setContentsMargins(0,12,0,0); gen_l.setSpacing(12)
        card1 = QFrame(); card1.setObjectName("card")
        fl1 = QFormLayout(card1); fl1.setSpacing(12); fl1.setContentsMargins(20,20,20,20)
        self.root = QLineEdit()
        self.root.setPlaceholderText("e.g. Z:\\QMS  or  \\\\server\\share\\QMS  or  G:\\My Drive\\QMS")
        br_btn = make_btn("Browse…","sec"); br_btn.clicked.connect(self._browse)
        rr = QHBoxLayout(); rr.addWidget(self.root); rr.addWidget(br_btn)
        self.user    = QLineEdit(); self.user.setPlaceholderText("Your full name")
        self.email   = QLineEdit(); self.email.setPlaceholderText("your@email.com")
        self.company = QLineEdit(); self.company.setPlaceholderText("Company or client name")
        fl1.addRow("QMS Root Folder *:", rr)
        fl1.addRow("Your Name:", self.user)
        fl1.addRow("Your Email:", self.email)
        fl1.addRow("Company / Client Name:", self.company)
        gen_l.addWidget(card1)
        n1 = QLabel("QMS Root can be a local path, mapped network drive, UNC path, or cloud sync folder (Google Drive, OneDrive). All team members must point to the same root.")
        n1.setWordWrap(True); n1.setStyleSheet("color:#505870;font-size:13px;")
        gen_l.addWidget(n1); gen_l.addStretch()
        tabs.addTab(gen_w, "General")

        # ── Tab 2: Client & Project Config ─────────────────────────────────
        cli_w = QWidget(); cli_l = QVBoxLayout(cli_w)
        cli_l.setContentsMargins(0,12,0,0); cli_l.setSpacing(12)

        card2 = QFrame(); card2.setObjectName("card")
        fl2 = QFormLayout(card2); fl2.setSpacing(12); fl2.setContentsMargins(20,20,20,20)
        self.company_code = QLineEdit(); self.company_code.setPlaceholderText("e.g. ABC (2-4 letters)")
        self.company_code.setMaximumWidth(120)

        # Project list
        proj_lbl = QLabel("Projects:")
        proj_lbl.setStyleSheet("color:#C8D0E8;font-size:15px;font-weight:bold;")
        self.proj_table = QTableWidget(0, 3)
        self.proj_table.setHorizontalHeaderLabels(["Project Code", "Project Name", "Remove"])
        self.proj_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.proj_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.proj_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.proj_table.setMaximumHeight(180)
        self.proj_table.verticalHeader().setVisible(False)
        self.proj_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        add_proj_row = QHBoxLayout(); add_proj_row.setSpacing(8)
        self.new_proj_code = QLineEdit(); self.new_proj_code.setPlaceholderText("P001")
        self.new_proj_code.setMaximumWidth(100)
        self.new_proj_name = QLineEdit(); self.new_proj_name.setPlaceholderText("Project or device name")
        add_proj_btn = make_btn("+ Add Project", "primary")
        add_proj_btn.setStyleSheet("background:#4080FF;color:#FFF;border:none;padding:8px 16px;border-radius:6px;font-weight:bold;font-size:14px;")
        add_proj_btn.clicked.connect(self._add_project)
        add_proj_row.addWidget(QLabel("Code:")); add_proj_row.addWidget(self.new_proj_code)
        add_proj_row.addWidget(QLabel("Name:")); add_proj_row.addWidget(self.new_proj_name)
        add_proj_row.addWidget(add_proj_btn); add_proj_row.addStretch()

        fl2.addRow("Company Code:", self.company_code)
        cli_l.addWidget(card2)
        cli_l.addWidget(proj_lbl)
        cli_l.addWidget(self.proj_table)
        cli_l.addLayout(add_proj_row)
        n2 = QLabel("Company Code is used as a prefix in part numbers (e.g. ABC-P001-M001). Projects appear as a dropdown when creating project-level documents — document IDs will be prefixed with the project code (e.g. P001-SOP-007).")
        n2.setWordWrap(True); n2.setStyleSheet("color:#505870;font-size:13px;")
        cli_l.addWidget(n2); cli_l.addStretch()
        tabs.addTab(cli_w, "Client & Projects")

        # ── Tab 3: Document Appearance ──────────────────────────────────────
        app_w = QWidget(); app_l = QVBoxLayout(app_w)
        app_l.setContentsMargins(0,12,0,0); app_l.setSpacing(12)
        card3 = QFrame(); card3.setObjectName("card")
        fl3 = QFormLayout(card3); fl3.setSpacing(12); fl3.setContentsMargins(20,20,20,20)
        self.hdr_color = QLineEdit(); self.hdr_color.setPlaceholderText("003F7F (hex, no #)")
        self.hdr_color.setMaximumWidth(160)
        self.hdr_font  = QComboBox()
        self.hdr_font.addItems(["Arial","Calibri","Times New Roman","Georgia","Helvetica","Garamond"])
        self.logo_path = QLineEdit(); self.logo_path.setPlaceholderText("Path to logo .png or .jpg (optional)")
        logo_btn = make_btn("Browse…","sec"); logo_btn.clicked.connect(self._browse_logo)
        logo_row = QHBoxLayout(); logo_row.addWidget(self.logo_path); logo_row.addWidget(logo_btn)
        self.doc_font_size = QSpinBox(); self.doc_font_size.setRange(8,16); self.doc_font_size.setValue(11)
        self.doc_font_size.setMaximumWidth(80)
        self.cr_color = QLineEdit(); self.cr_color.setPlaceholderText("8B1A00 (hex, no #)")
        self.cr_color.setMaximumWidth(160)
        fl3.addRow("Header Color (hex):", self.hdr_color)
        fl3.addRow("CR Number Color (hex):", self.cr_color)
        fl3.addRow("Document Font:", self.hdr_font)
        fl3.addRow("Body Font Size (pt):", self.doc_font_size)
        fl3.addRow("Company Logo:", logo_row)
        app_l.addWidget(card3)
        n3 = QLabel("These settings apply to all newly generated documents. Existing documents are not affected — they retain their formatting. To apply new branding to existing docs, open them in Word and reformat manually.")
        n3.setWordWrap(True); n3.setStyleSheet("color:#505870;font-size:13px;")
        app_l.addWidget(n3); app_l.addStretch()
        tabs.addTab(app_w, "Document Appearance")

        # ── Tab 4: Document Numbering ───────────────────────────────────────
        num_w = QWidget(); num_l = QVBoxLayout(num_w)
        num_l.setContentsMargins(0,12,0,0); num_l.setSpacing(12)
        card4 = QFrame(); card4.setObjectName("card")
        fl4 = QFormLayout(card4); fl4.setSpacing(12); fl4.setContentsMargins(20,20,20,20)
        self.num_padding = QSpinBox(); self.num_padding.setRange(2,6); self.num_padding.setValue(3)
        self.num_padding.setMaximumWidth(80)
        self.num_padding.setToolTip("Number of digits in doc number: 3 = SOP-001, 4 = SOP-0001")
        self.proj_doc_prefix = QComboBox()
        self.proj_doc_prefix.addItems([
            "Project code prefix: P001-SOP-007",
            "Project code suffix: SOP-007-P001",
            "No project code in doc number",
        ])
        fl4.addRow("Number Padding (digits):", self.num_padding)
        fl4.addRow("Project Doc Numbering:", self.proj_doc_prefix)

        # Prefix table
        pfx_lbl = QLabel("Document Type Prefixes:")
        pfx_lbl.setStyleSheet("color:#C8D0E8;font-size:15px;font-weight:bold;")
        self.pfx_table = QTableWidget(0, 3)
        self.pfx_table.setHorizontalHeaderLabels(["Prefix","Document Type Name","Scope"])
        self.pfx_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.pfx_table.setMaximumHeight(200)
        self.pfx_table.verticalHeader().setVisible(False)
        self.pfx_table.setEditTriggers(QAbstractItemView.DoubleClicked)

        num_l.addWidget(card4)
        num_l.addWidget(pfx_lbl)
        num_l.addWidget(self.pfx_table)
        n4 = QLabel("Double-click any prefix name or type to edit it. Changes apply to new documents only. Scope: QMS = controlled document, INFORMAL = not under QMS.")
        n4.setWordWrap(True); n4.setStyleSheet("color:#505870;font-size:13px;")
        num_l.addWidget(n4); num_l.addStretch()
        tabs.addTab(num_w, "Document Numbering")

        l.addWidget(tabs)
        self.tabs = tabs

        # Save button
        sb = make_btn("Save All Settings","primary")
        sb.setStyleSheet("background:#4080FF;color:#FFF;border:none;padding:11px 28px;"
                         "border-radius:6px;font-size:18px;font-weight:bold;")
        sb.clicked.connect(self._save)
        self.sl = QLabel("")
        self.sl.setStyleSheet("color:#30C070;font-size:15px;")
        l.addWidget(sb); l.addWidget(self.sl)
        self._load()

    def _load(self):
        cfg = api("get", "/config")
        if isinstance(cfg, dict) and not cfg.get("error"):
            self.root.setText(cfg.get("qms_root",""))
            self.user.setText(cfg.get("current_user",""))
            self.email.setText(cfg.get("current_email",""))
            self.company.setText(cfg.get("company_name",""))
            self.company_code.setText(cfg.get("company_code",""))
            self.hdr_color.setText(cfg.get("header_color","003F7F"))
            self.cr_color.setText(cfg.get("cr_color","8B1A00"))
            font = cfg.get("doc_font","Arial")
            idx = self.hdr_font.findText(font)
            if idx >= 0: self.hdr_font.setCurrentIndex(idx)
            self.doc_font_size.setValue(int(cfg.get("doc_font_size", 11)))
            self.logo_path.setText(cfg.get("logo_path",""))
            self.num_padding.setValue(int(cfg.get("number_padding", 3)))
            pfx_style = cfg.get("project_prefix_style", "prefix")
            style_map = {"prefix":0,"suffix":1,"none":2}
            self.proj_doc_prefix.setCurrentIndex(style_map.get(pfx_style, 0))
            self._load_projects(cfg.get("projects", {}))
            self._load_prefixes(cfg.get("prefix_scheme", {}),
                                cfg.get("informal_prefix_scheme", {}))

    def _load_projects(self, projects):
        self.proj_table.setRowCount(0)
        for code, name in (projects or {}).items():
            r = self.proj_table.rowCount(); self.proj_table.insertRow(r)
            self.proj_table.setItem(r, 0, QTableWidgetItem(code))
            self.proj_table.setItem(r, 1, QTableWidgetItem(name))
            rm = QPushButton("Remove")
            rm.setStyleSheet("background:#C03030;color:#FFF;border:none;padding:4px 10px;border-radius:4px;font-size:13px;")
            rm.clicked.connect(lambda _, c=code: self._remove_project(c))
            self.proj_table.setCellWidget(r, 2, rm)

    def _load_prefixes(self, formal, informal):
        self.pfx_table.setRowCount(0)
        for pfx, name in (formal or {}).items():
            r = self.pfx_table.rowCount(); self.pfx_table.insertRow(r)
            self.pfx_table.setItem(r,0,QTableWidgetItem(pfx))
            self.pfx_table.setItem(r,1,QTableWidgetItem(name))
            self.pfx_table.setItem(r,2,QTableWidgetItem("QMS"))
        for pfx, name in (informal or {}).items():
            r = self.pfx_table.rowCount(); self.pfx_table.insertRow(r)
            self.pfx_table.setItem(r,0,QTableWidgetItem(pfx))
            self.pfx_table.setItem(r,1,QTableWidgetItem(name))
            self.pfx_table.setItem(r,2,QTableWidgetItem("INFORMAL"))

    def _add_project(self):
        code = self.new_proj_code.text().strip().upper()
        name = self.new_proj_name.text().strip()
        if not code or not name:
            self.sl.setStyleSheet("color:#FF5050;font-size:15px;")
            self.sl.setText("⚠ Project code and name are required."); return
        cfg = api("get","/config")
        projects = cfg.get("projects", {})
        projects[code] = name
        api("post","/config", json={"projects": projects})
        self.new_proj_code.clear(); self.new_proj_name.clear()
        self._load_projects(projects)
        self.sl.setStyleSheet("color:#30C070;font-size:15px;")
        self.sl.setText(f"✓ Project {code} added.")

    def _remove_project(self, code):
        cfg = api("get","/config")
        projects = cfg.get("projects", {})
        projects.pop(code, None)
        api("post","/config", json={"projects": projects})
        self._load_projects(projects)

    def _browse(self):
        f = QFileDialog.getExistingDirectory(self,"Select QMS Root Folder")
        if f: self.root.setText(f)

    def _browse_logo(self):
        f, _ = QFileDialog.getOpenFileName(self,"Select Company Logo",
                                            "","Images (*.png *.jpg *.jpeg *.bmp)")
        if f: self.logo_path.setText(f)

    def _save(self):
        # Collect prefix edits from table
        formal_pfx = {}; informal_pfx = {}
        for row in range(self.pfx_table.rowCount()):
            pfx  = (self.pfx_table.item(row,0) or QTableWidgetItem("")).text().strip()
            name = (self.pfx_table.item(row,1) or QTableWidgetItem("")).text().strip()
            scope= (self.pfx_table.item(row,2) or QTableWidgetItem("QMS")).text().strip()
            if pfx and name:
                if scope.upper() == "INFORMAL":
                    informal_pfx[pfx] = name
                else:
                    formal_pfx[pfx] = name

        style_map = {0:"prefix", 1:"suffix", 2:"none"}
        payload = {
            "qms_root":             self.root.text().strip(),
            "current_user":         self.user.text().strip(),
            "current_email":        self.email.text().strip(),
            "company_name":         self.company.text().strip(),
            "company_code":         self.company_code.text().strip().upper(),
            "header_color":         self.hdr_color.text().strip().lstrip("#"),
            "cr_color":             self.cr_color.text().strip().lstrip("#"),
            "doc_font":             self.hdr_font.currentText(),
            "doc_font_size":        self.doc_font_size.value(),
            "logo_path":            self.logo_path.text().strip(),
            "number_padding":       self.num_padding.value(),
            "project_prefix_style": style_map.get(self.proj_doc_prefix.currentIndex(),"prefix"),
        }
        if formal_pfx:   payload["prefix_scheme"]          = formal_pfx
        if informal_pfx: payload["informal_prefix_scheme"]  = informal_pfx

        r = api("post","/config", json=payload)
        if r.get("ok"):
            self.sl.setStyleSheet("color:#30C070;font-size:15px;")
            self.sl.setText("✓ All settings saved.")
        else:
            self.sl.setStyleSheet("color:#FF5050;font-size:15px;")
            self.sl.setText(f"Error: {r.get('error','Unknown error')}")

    def refresh(self):
        fw = QApplication.focusWidget()
        if fw in (self.root, self.user, self.email, self.company,
                  self.company_code, self.hdr_color, self.cr_color,
                  self.logo_path, self.new_proj_code, self.new_proj_name):
            return
        self._load()

# ── MAIN WINDOW ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QMS Document Management System v1.4")
        self.setMinimumSize(1300,800); self.resize(1500,900)
        self.setStyleSheet(STYLE)
        central = QWidget(); self.setCentralWidget(central)
        ml = QHBoxLayout(central); ml.setContentsMargins(0,0,0,0); ml.setSpacing(0)

        # ── Sidebar ──
        sb = QFrame(); sb.setObjectName("sidebar"); sb.setFixedWidth(240)
        sl = QVBoxLayout(sb); sl.setContentsMargins(0,0,0,0); sl.setSpacing(0)
        logo = QLabel("QMS"); logo.setObjectName("logo_label")
        logo.setFont(QFont("Segoe UI",22,QFont.Bold))
        sub  = QLabel("Document Control v1.4"); sub.setObjectName("sub_label")
        sub.setFont(QFont("Segoe UI",11))
        sl.addWidget(logo); sl.addWidget(sub)

        self.nav_btns  = []
        self.badge_lbs = []
        self.pages     = QStackedWidget()
        self.page_objs = []

        page_classes = [DashboardPage, DocumentsPage, NewDocPage,
                        RoutingPage, NotificationsPage, TeamRosterPage,
                        ReviewDuePage, AuditLogPage, SettingsPage]
        page_args    = [(),(),( self._on_created,),(),(),(),(),(),()]

        for i,(label,icon,has_badge) in enumerate(NAV_ITEMS):
            row_w = QWidget(); row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(0,0,0,0); row_l.setSpacing(0)
            btn = QPushButton(f"  {icon}  {label}")
            btn.setFont(QFont("Segoe UI",15))
            btn.setFixedHeight(42)
            btn.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
            btn.clicked.connect(lambda _,idx=i: self._nav(idx))
            row_l.addWidget(btn)
            badge = QLabel("")
            badge.setFixedSize(20,20)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet("background:#FF4444;color:#FFF;border-radius:10px;"
                                "font-size:12px;font-weight:bold;")
            badge.hide()
            row_l.addWidget(badge)
            row_l.addSpacing(8)
            sl.addWidget(row_w)
            self.nav_btns.append(btn)
            self.badge_lbs.append(badge)
            pg = page_classes[i](*page_args[i])
            self.pages.addWidget(pg); self.page_objs.append(pg)

        sl.addStretch()
        self.srv_lbl = QLabel("● Starting…")
        self.srv_lbl.setStyleSheet("color:#E8A020;font-size:12px;padding:12px 20px;")
        sl.addWidget(self.srv_lbl)
        ml.addWidget(sb); ml.addWidget(self.pages)
        self._nav(0)

        self.timer = QTimer(); self.timer.timeout.connect(self._auto_refresh)
        self.timer.start(30000)
        self.badge_timer = QTimer(); self.badge_timer.timeout.connect(self._update_badges)
        self.badge_timer.start(15000)

    def _nav(self, idx):
        self.pages.setCurrentIndex(idx)
        active_style = ("QPushButton{background:#1A2040;color:#FFF;border:none;"
                        "border-left:3px solid #4080FF;padding:12px 20px;"
                        "text-align:left;font-size:16px;}")
        normal_style = ("QPushButton{background:transparent;color:#8890A8;border:none;"
                        "padding:12px 20px;text-align:left;font-size:16px;}"
                        "QPushButton:hover{background:#141824;color:#C8D0E8;}")
        for i,btn in enumerate(self.nav_btns):
            btn.setStyleSheet(active_style if i==idx else normal_style)
        pg = self.page_objs[idx]
        if hasattr(pg,"refresh"): pg.refresh()

    def _on_created(self):
        if hasattr(self.page_objs[0],"refresh"): self.page_objs[0].refresh()

    def _auto_refresh(self):
        idx = self.pages.currentIndex()
        # Never auto-refresh Settings page (index 8) — overwrites fields mid-entry
        if idx == 8:
            return
        # Skip if user is actively typing in any input field
        fw = QApplication.focusWidget()
        if fw is not None:
            if isinstance(fw, (QLineEdit, QTextEdit, QSpinBox, QComboBox)):
                return
        pg = self.page_objs[idx]
        if hasattr(pg, "refresh"): pg.refresh()

    def _update_badges(self):
        stats = api("get","/stats")
        if isinstance(stats,dict):
            # Routing badge (index 3)
            pr = (stats.get("pending_reviews",0) or 0) + (stats.get("pending_approvals",0) or 0)
            self._set_badge(3, pr)
            # Notifications badge (index 4)
            self._set_badge(4, stats.get("unread_notifs",0) or 0)

    def _set_badge(self, nav_idx, count):
        badge = self.badge_lbs[nav_idx]
        if count and count > 0:
            badge.setText(str(count) if count < 100 else "99+")
            badge.show()
        else:
            badge.hide()

    def set_server_ready(self):
        self.srv_lbl.setText("● Server running")
        self.srv_lbl.setStyleSheet("color:#30C070;font-size:12px;padding:12px 20px;")
        self.page_objs[0].refresh(); self._update_badges()

    def set_server_failed(self, msg):
        self.srv_lbl.setText("● Server offline")
        self.srv_lbl.setStyleSheet("color:#FF5050;font-size:12px;padding:12px 20px;")

# ── SPLASH ────────────────────────────────────────────────────────────────────

class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.SplashScreen|Qt.FramelessWindowHint)
        self.setFixedSize(420,240)
        self.setStyleSheet("background:#080A0F;border:1px solid #1E2130;border-radius:12px;")
        l = QVBoxLayout(self); l.setContentsMargins(40,40,40,40); l.setSpacing(12)
        t = QLabel("QMS"); t.setFont(QFont("Segoe UI",60,QFont.Bold))
        t.setStyleSheet("color:#4080FF;"); t.setAlignment(Qt.AlignCenter)
        s = QLabel("Document Management System v1.4")
        s.setStyleSheet("color:#8890A8;font-size:16px;"); s.setAlignment(Qt.AlignCenter)
        self.status = QLabel("Starting server…")
        self.status.setStyleSheet("color:#505870;font-size:14px;"); self.status.setAlignment(Qt.AlignCenter)
        bar = QProgressBar(); bar.setRange(0,0); bar.setFixedHeight(3)
        for w in [t,s,self.status,bar]: l.addWidget(w)
        sc = QApplication.primaryScreen().geometry()
        self.move((sc.width()-self.width())//2,(sc.height()-self.height())//2)

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv); app.setStyle("Fusion")
    from PyQt5.QtGui import QFont as _QF
    app.setFont(_QF("Segoe UI", 14))
    splash = SplashScreen(); splash.show(); app.processEvents()
    win = MainWindow()
    def on_ready():
        splash.close(); win.show(); win.set_server_ready()
    def on_failed(msg):
        splash.status.setText(f"Error: {msg}")
        QTimer.singleShot(2000, lambda: (splash.close(), win.show(), win.set_server_failed(msg)))
    srv = ServerThread(); srv.ready.connect(on_ready); srv.failed.connect(on_failed)
    srv.start()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
