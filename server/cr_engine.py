#!/usr/bin/env python3
"""Simple CR engine persisted to _REGISTER JSON files."""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Dict, List, Optional


class CREngine:
    def __init__(self, qms_root: Path):
        self.root = Path(qms_root)
        self.reg_dir = self.root / "_REGISTER"
        self.cr_file = self.reg_dir / "change_requests.json"
        self.log_file = self.reg_dir / "change_requests_log.json"
        self._ensure_files()

    def _ensure_files(self) -> None:
        self.reg_dir.mkdir(parents=True, exist_ok=True)
        if not self.cr_file.exists():
            self.cr_file.write_text("[]", encoding="utf-8")
        if not self.log_file.exists():
            self.log_file.write_text("[]", encoding="utf-8")

    def _load_json(self, path: Path) -> List[Dict]:
        try:
            data = json.loads(path.read_text(encoding="utf-8") or "[]")
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save_json(self, path: Path, data: List[Dict]) -> None:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _today(self) -> str:
        return datetime.date.today().isoformat()

    def _next_cr_id(self) -> str:
        crs = self._load_json(self.cr_file)
        nums = []
        for cr in crs:
            cid = str(cr.get("cr_id", ""))
            if cid.startswith("CR-"):
                try:
                    nums.append(int(cid.split("-", 1)[1]))
                except Exception:
                    pass
        nxt = (max(nums) + 1) if nums else 1
        return f"CR-{nxt:04d}"

    def _log(self, action: str, cr_id: str, actor: str, notes: str = "") -> None:
        rows = self._load_json(self.log_file)
        rows.append(
            {
                "ts": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "action": action,
                "cr_id": cr_id,
                "actor": actor,
                "notes": notes,
            }
        )
        self._save_json(self.log_file, rows)

    def list_crs(self, status: Optional[str] = None) -> List[Dict]:
        rows = self._load_json(self.cr_file)
        if status:
            rows = [r for r in rows if str(r.get("status", "")).upper() == status.upper()]
        return sorted(rows, key=lambda r: r.get("created_date", ""), reverse=True)

    def get_cr(self, cr_id: str) -> Optional[Dict]:
        for cr in self._load_json(self.cr_file):
            if cr.get("cr_id") == cr_id:
                return cr
        return None

    def create_cr(
        self,
        title: str,
        description: str,
        reason: str,
        change_type: str,
        initiator: str,
        initiator_email: str,
        linked_doc_ids,
        risk_ref: str,
        impact_analysis: str,
        training_required: str,
        training_notes: str,
        target_effective_date: str,
    ) -> Dict:
        rows = self._load_json(self.cr_file)
        linked = linked_doc_ids if isinstance(linked_doc_ids, list) else []
        cr = {
            "cr_id": self._next_cr_id(),
            "title": title or "Untitled Change Request",
            "description": description or "",
            "reason": reason or "",
            "change_type": change_type or "Process Change",
            "initiator": initiator or "",
            "initiator_email": initiator_email or "",
            "linked_doc_ids": ",".join([d.strip() for d in linked if str(d).strip()]),
            "risk_ref": risk_ref or "",
            "impact_analysis": impact_analysis or "",
            "training_required": (training_required or "NO").upper(),
            "training_notes": training_notes or "",
            "target_effective_date": target_effective_date or "",
            "effective_date": "",
            "status": "DRAFT",
            "created_date": self._today(),
            "last_modified": self._today(),
            "approved_by": "",
            "closed_by": "",
            "post_impl_notes": "",
            "cancel_reason": "",
            "cr_form_doc_id": "",
        }
        rows.append(cr)
        self._save_json(self.cr_file, rows)
        self._log("CR_CREATED", cr["cr_id"], initiator or "", cr["title"])
        return cr

    def update_cr(self, cr_id: str, updates: Dict, user: str) -> Dict:
        rows = self._load_json(self.cr_file)
        for cr in rows:
            if cr.get("cr_id") == cr_id:
                for k, v in (updates or {}).items():
                    if k in ("cr_id", "created_date"):
                        continue
                    cr[k] = v
                cr["last_modified"] = self._today()
                self._save_json(self.cr_file, rows)
                self._log("CR_UPDATED", cr_id, user or "", "Fields updated")
                return {"ok": True, "cr": cr}
        return {"ok": False, "error": "CR not found."}

    def link_document(self, cr_id: str, doc_id: str, user: str) -> Dict:
        rows = self._load_json(self.cr_file)
        for cr in rows:
            if cr.get("cr_id") == cr_id:
                cur = [d.strip() for d in str(cr.get("linked_doc_ids", "")).split(",") if d.strip()]
                if doc_id and doc_id not in cur:
                    cur.append(doc_id)
                cr["linked_doc_ids"] = ",".join(cur)
                cr["last_modified"] = self._today()
                self._save_json(self.cr_file, rows)
                self._log("CR_LINK_DOC", cr_id, user or "", doc_id)
                return {"ok": True, "cr": cr}
        return {"ok": False, "error": "CR not found."}

    def unlink_document(self, cr_id: str, doc_id: str, user: str) -> Dict:
        rows = self._load_json(self.cr_file)
        for cr in rows:
            if cr.get("cr_id") == cr_id:
                cur = [d.strip() for d in str(cr.get("linked_doc_ids", "")).split(",") if d.strip()]
                cur = [d for d in cur if d != doc_id]
                cr["linked_doc_ids"] = ",".join(cur)
                cr["last_modified"] = self._today()
                self._save_json(self.cr_file, rows)
                self._log("CR_UNLINK_DOC", cr_id, user or "", doc_id)
                return {"ok": True, "cr": cr}
        return {"ok": False, "error": "CR not found."}

    def submit_cr_for_review(self, cr_id: str, user: str) -> Dict:
        return self._set_status(cr_id, "IN_REVIEW", user, "CR_SUBMIT_REVIEW")

    def approve_cr(self, cr_id: str, user: str, effective_date: str = "") -> Dict:
        rows = self._load_json(self.cr_file)
        for cr in rows:
            if cr.get("cr_id") == cr_id:
                cr["status"] = "APPROVED"
                cr["approved_by"] = user or ""
                if effective_date:
                    cr["effective_date"] = effective_date
                cr["last_modified"] = self._today()
                self._save_json(self.cr_file, rows)
                linked = [d.strip() for d in str(cr.get("linked_doc_ids", "")).split(",") if d.strip()]
                self._log("CR_APPROVED", cr_id, user or "", ",".join(linked))
                return {"ok": True, "cr": cr, "linked_docs": linked}
        return {"ok": False, "error": "CR not found."}

    def make_effective(self, cr_id: str, user: str, effective_date: str = "") -> Dict:
        rows = self._load_json(self.cr_file)
        for cr in rows:
            if cr.get("cr_id") == cr_id:
                cr["status"] = "EFFECTIVE"
                cr["effective_date"] = effective_date or self._today()
                cr["last_modified"] = self._today()
                self._save_json(self.cr_file, rows)
                linked = [d.strip() for d in str(cr.get("linked_doc_ids", "")).split(",") if d.strip()]
                self._log("CR_EFFECTIVE", cr_id, user or "", cr["effective_date"])
                return {"ok": True, "cr": cr, "linked_docs": linked}
        return {"ok": False, "error": "CR not found."}

    def close_cr(self, cr_id: str, user: str, post_impl_notes: str = "") -> Dict:
        rows = self._load_json(self.cr_file)
        for cr in rows:
            if cr.get("cr_id") == cr_id:
                cr["status"] = "CLOSED"
                cr["closed_by"] = user or ""
                cr["post_impl_notes"] = post_impl_notes or ""
                cr["last_modified"] = self._today()
                self._save_json(self.cr_file, rows)
                self._log("CR_CLOSED", cr_id, user or "", post_impl_notes or "")
                return {"ok": True, "cr": cr}
        return {"ok": False, "error": "CR not found."}

    def cancel_cr(self, cr_id: str, user: str, reason: str = "") -> Dict:
        rows = self._load_json(self.cr_file)
        for cr in rows:
            if cr.get("cr_id") == cr_id:
                cr["status"] = "CANCELLED"
                cr["cancel_reason"] = reason or ""
                cr["last_modified"] = self._today()
                self._save_json(self.cr_file, rows)
                self._log("CR_CANCELLED", cr_id, user or "", reason or "")
                return {"ok": True, "cr": cr}
        return {"ok": False, "error": "CR not found."}

    def get_pending_effective(self) -> List[Dict]:
        return [cr for cr in self._load_json(self.cr_file) if cr.get("status") == "APPROVED"]

    def get_log(self, cr_id: Optional[str] = None) -> List[Dict]:
        rows = self._load_json(self.log_file)
        if cr_id:
            rows = [r for r in rows if r.get("cr_id") == cr_id]
        return rows

    def get_stats(self) -> Dict:
        rows = self._load_json(self.cr_file)
        counts: Dict[str, int] = {"total": len(rows), "pending_effective": 0}
        for cr in rows:
            st = str(cr.get("status", "")).upper()
            counts[st] = counts.get(st, 0) + 1
            if st == "APPROVED":
                counts["pending_effective"] += 1
        return counts

    def _set_status(self, cr_id: str, status: str, user: str, action: str) -> Dict:
        rows = self._load_json(self.cr_file)
        for cr in rows:
            if cr.get("cr_id") == cr_id:
                cr["status"] = status
                cr["last_modified"] = self._today()
                self._save_json(self.cr_file, rows)
                self._log(action, cr_id, user or "")
                return {"ok": True, "cr": cr}
        return {"ok": False, "error": "CR not found."}
