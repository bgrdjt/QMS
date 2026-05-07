#!/usr/bin/env python3
"""
QMS Routing Engine v1.4
Changes from v1.1:
- Multi-role support per person (roles is now a list)
- Role history tracking with effective dates
- Customizable role list per client (stored in config)
- Hardened JSON responses throughout
"""

import json, datetime, uuid
from pathlib import Path

# ── DEFAULT ROLES (overridable per client in dms_config.json) ─────────────────
DEFAULT_ROLES = [
    "Author",
    "Reviewer",
    "Technical Reviewer",
    "QA Reviewer",
    "Approver",
    "QA Lead",
    "Project Manager",
    "Regulatory Affairs",
    "Observer",
    "Administrator",
]

ROUTE_STATUS = {
    "PENDING":   "PENDING",
    "ACCEPTED":  "ACCEPTED",
    "REVIEWED":  "REVIEWED",
    "APPROVED":  "APPROVED",
    "REJECTED":  "REJECTED",
    "RECALLED":  "RECALLED",
    "EXPIRED":   "EXPIRED",
}

ROUTE_TYPE = {
    "REVIEW":   "REVIEW",
    "APPROVAL": "APPROVAL",
    "FYI":      "FYI",
}

NOTIFICATION_TYPE = {
    "REVIEW_REQUESTED":   "REVIEW_REQUESTED",
    "APPROVAL_REQUESTED": "APPROVAL_REQUESTED",
    "REVIEW_COMPLETE":    "REVIEW_COMPLETE",
    "REVIEW_REJECTED":    "REVIEW_REJECTED",
    "DOCUMENT_APPROVED":  "DOCUMENT_APPROVED",
    "DOCUMENT_RECALLED":  "DOCUMENT_RECALLED",
    "REVIEW_DUE_SOON":    "REVIEW_DUE_SOON",
    "REVIEW_OVERDUE":     "REVIEW_OVERDUE",
    "FYI":                "FYI",
}


class RoutingEngine:
    def __init__(self, qms_root: Path):
        self.root        = Path(qms_root)
        self.queue_file  = self.root / "_REGISTER" / "review_queue.json"
        self.notif_file  = self.root / "_REGISTER" / "notifications.json"
        self.roster_file = self.root / "_REGISTER" / "team_roster.json"
        self._ensure_files()

    # ── FILE I/O ──────────────────────────────────────────────────────────────

    def _ensure_files(self):
        for f in [self.queue_file, self.notif_file]:
            if not f.exists():
                f.write_text("[]")
        if not self.roster_file.exists():
            self.roster_file.write_text(json.dumps(
                {"members": [], "custom_roles": DEFAULT_ROLES}, indent=2))

    def _load(self, path):
        try:
            text = path.read_text().strip()
            if not text:
                return [] if "queue" in str(path) or "notif" in str(path) else {}
            return json.loads(text)
        except Exception:
            return [] if "queue" in str(path) or "notif" in str(path) else {}

    def _save(self, path, data):
        path.write_text(json.dumps(data, indent=2))

    def load_queue(self):         return self._load(self.queue_file)
    def load_notifications(self): return self._load(self.notif_file)

    def load_roster(self):
        data = self._load(self.roster_file)
        if isinstance(data, list):
            # Migrate old list-only format
            data = {"members": data, "custom_roles": DEFAULT_ROLES}
            self._save(self.roster_file, data)
        return data

    def save_queue(self, q):         self._save(self.queue_file, q)
    def save_notifications(self, n): self._save(self.notif_file, n)

    def save_roster(self, roster):
        if isinstance(roster, list):
            roster = {"members": roster, "custom_roles": DEFAULT_ROLES}
        self._save(self.roster_file, roster)

    # ── ROLE MANAGEMENT ───────────────────────────────────────────────────────

    def get_custom_roles(self):
        """Return the client-configured role list."""
        roster = self.load_roster()
        return roster.get("custom_roles", DEFAULT_ROLES)

    def set_custom_roles(self, roles: list):
        """Replace the client role list."""
        roster = self.load_roster()
        roster["custom_roles"] = roles
        self.save_roster(roster)
        return {"ok": True, "roles": roles}

    def add_custom_role(self, role: str):
        roles = self.get_custom_roles()
        if role not in roles:
            roles.append(role)
            self.set_custom_roles(roles)
        return {"ok": True, "roles": roles}

    def remove_custom_role(self, role: str):
        roles = self.get_custom_roles()
        roles = [r for r in roles if r != role]
        self.set_custom_roles(roles)
        return {"ok": True, "roles": roles}

    # ── TEAM ROSTER ───────────────────────────────────────────────────────────

    def get_members(self):
        return self.load_roster().get("members", [])

    def add_member(self, name, email, roles=None, doc_types=None):
        """
        roles: list of role strings (multi-role support)
        Backward compat: if a single string is passed, wrap it in a list.
        """
        roster  = self.load_roster()
        members = roster.get("members", [])

        # Normalize roles to list
        if roles is None:
            roles = ["Reviewer"]
        elif isinstance(roles, str):
            roles = [roles]

        # Deduplicate email
        if any(m["email"].lower() == email.lower() for m in members):
            return {"error": "A member with this email already exists"}

        today = datetime.date.today().isoformat()
        member = {
            "member_id":    str(uuid.uuid4())[:8],
            "name":         name,
            "email":        email,
            "roles":        roles,          # current active roles (list)
            "role_history": [               # audit trail of role changes
                {
                    "roles":       roles,
                    "changed_date": today,
                    "changed_by":  "System",
                    "reason":      "Initial assignment"
                }
            ],
            "doc_types":    doc_types or [],
            "active":       True,
            "added_date":   today,
        }
        members.append(member)
        roster["members"] = members
        self.save_roster(roster)
        return {"ok": True, "member": member}

    def update_member(self, member_id, updates, changed_by="System", reason=""):
        """
        Update member fields. If 'roles' is in updates, records a role history entry.
        """
        roster  = self.load_roster()
        today   = datetime.date.today().isoformat()
        updated = False

        for m in roster.get("members", []):
            if m["member_id"] == member_id:
                # Normalize incoming roles to list
                if "roles" in updates:
                    new_roles = updates["roles"]
                    if isinstance(new_roles, str):
                        new_roles = [new_roles]
                    updates["roles"] = new_roles

                    # Only record history if roles actually changed
                    old_roles = m.get("roles", [])
                    if isinstance(old_roles, str):
                        old_roles = [old_roles]

                    if set(new_roles) != set(old_roles):
                        if "role_history" not in m:
                            m["role_history"] = []
                        m["role_history"].append({
                            "roles":        new_roles,
                            "changed_date": today,
                            "changed_by":   changed_by,
                            "reason":       reason or "Role updated"
                        })

                # Handle legacy single 'role' field migration
                if "role" in updates and "roles" not in updates:
                    updates["roles"] = [updates.pop("role")]

                m.update(updates)
                updated = True
                break

        if updated:
            self.save_roster(roster)
            return {"ok": True}
        return {"error": "Member not found"}

    def remove_member(self, member_id):
        roster = self.load_roster()
        roster["members"] = [m for m in roster.get("members", [])
                              if m["member_id"] != member_id]
        self.save_roster(roster)
        return {"ok": True}

    def get_member_role_history(self, member_id):
        """Return full role history for a specific member."""
        for m in self.get_members():
            if m["member_id"] == member_id:
                return m.get("role_history", [])
        return []

    def get_roles_at_date(self, member_id, target_date: str):
        """
        Return what roles a member held on a specific date.
        Used for historical audit accuracy.
        """
        history = self.get_member_role_history(member_id)
        if not history:
            return []
        # Find the most recent role change on or before target_date
        relevant = [h for h in history if h["changed_date"] <= target_date]
        if not relevant:
            return history[0]["roles"] if history else []
        relevant.sort(key=lambda h: h["changed_date"])
        return relevant[-1]["roles"]

    def get_default_reviewers(self, doc_type):
        """Return active members who default-review this doc type and have a reviewer-type role."""
        reviewer_roles = {"Reviewer", "Technical Reviewer", "QA Reviewer",
                          "QA Lead", "Administrator"}
        members = self.get_members()
        result = []
        for m in members:
            if not m.get("active"):
                continue
            member_roles = m.get("roles", [])
            if isinstance(member_roles, str):
                member_roles = [member_roles]
            has_reviewer_role = bool(set(member_roles) & reviewer_roles)
            in_doc_types = (doc_type in m.get("doc_types", []) or
                            "ALL" in m.get("doc_types", []))
            if has_reviewer_role and in_doc_types:
                result.append(m)
        return result

    def get_default_approver(self, doc_type):
        """Return the first active approver for a doc type."""
        approver_roles = {"Approver", "QA Lead", "Administrator"}
        members = self.get_members()
        for m in members:
            if not m.get("active"):
                continue
            member_roles = m.get("roles", [])
            if isinstance(member_roles, str):
                member_roles = [member_roles]
            has_approver_role = bool(set(member_roles) & approver_roles)
            in_doc_types = (doc_type in m.get("doc_types", []) or
                            "ALL" in m.get("doc_types", []))
            if has_approver_role and in_doc_types:
                return m
        return None

    # ── ROUTING ───────────────────────────────────────────────────────────────

    def submit_for_review(self, doc_id, doc_title, doc_version,
                          reviewers, sender_name, sender_email="",
                          notes="", due_days=7):
        queue  = self.load_queue()
        notifs = self.load_notifications()
        today  = datetime.date.today()
        due    = (today + datetime.timedelta(days=due_days)).isoformat()
        created = []

        for reviewer in reviewers:
            route_id = f"RV-{str(uuid.uuid4())[:8].upper()}"
            # Snapshot reviewer's current roles for historical accuracy
            reviewer_roles = reviewer.get("roles", reviewer.get("role", "Reviewer"))
            if isinstance(reviewer_roles, str):
                reviewer_roles = [reviewer_roles]

            entry = {
                "route_id":              route_id,
                "doc_id":                doc_id,
                "doc_title":             doc_title,
                "doc_version":           doc_version,
                "route_type":            ROUTE_TYPE["REVIEW"],
                "status":                ROUTE_STATUS["PENDING"],
                "assigned_to_name":      reviewer.get("name", ""),
                "assigned_to_email":     reviewer.get("email", ""),
                "assigned_to_roles":     reviewer_roles,   # snapshot at time of routing
                "assigned_by_name":      sender_name,
                "assigned_by_email":     sender_email,
                "created_date":          today.isoformat(),
                "due_date":              due,
                "completed_date":        "",
                "notes_from_reviewer":   "",
                "notes_from_sender":     notes,
                "notification_sent":     False,
                "notification_method":   ""
            }
            queue.append(entry)
            created.append(entry)
            notif = self._build_notification(
                route_id=route_id, doc_id=doc_id, recipient=reviewer,
                notif_type=NOTIFICATION_TYPE["REVIEW_REQUESTED"],
                doc_title=doc_title, doc_version=doc_version,
                sender=sender_name, notes=notes, due=due)
            notifs.append(notif)

        self.save_queue(queue)
        self.save_notifications(notifs)
        return created

    def submit_for_approval(self, doc_id, doc_title, doc_version,
                            approver, sender_name, sender_email="", notes=""):
        queue  = self.load_queue()
        notifs = self.load_notifications()
        today  = datetime.date.today().isoformat()
        route_id = f"AP-{str(uuid.uuid4())[:8].upper()}"
        approver_roles = approver.get("roles", approver.get("role", "Approver"))
        if isinstance(approver_roles, str):
            approver_roles = [approver_roles]

        entry = {
            "route_id":            route_id,
            "doc_id":              doc_id,
            "doc_title":           doc_title,
            "doc_version":         doc_version,
            "route_type":          ROUTE_TYPE["APPROVAL"],
            "status":              ROUTE_STATUS["PENDING"],
            "assigned_to_name":    approver.get("name", ""),
            "assigned_to_email":   approver.get("email", ""),
            "assigned_to_roles":   approver_roles,
            "assigned_by_name":    sender_name,
            "assigned_by_email":   sender_email,
            "created_date":        today,
            "due_date":            "",
            "completed_date":      "",
            "notes_from_reviewer": "",
            "notes_from_sender":   notes,
            "notification_sent":   False,
            "notification_method": ""
        }
        queue.append(entry)
        notif = self._build_notification(
            route_id=route_id, doc_id=doc_id, recipient=approver,
            notif_type=NOTIFICATION_TYPE["APPROVAL_REQUESTED"],
            doc_title=doc_title, doc_version=doc_version,
            sender=sender_name, notes=notes)
        notifs.append(notif)
        self.save_queue(queue)
        self.save_notifications(notifs)
        return entry

    def complete_review(self, route_id, reviewer_name, notes="", rejected=False):
        queue  = self.load_queue()
        notifs = self.load_notifications()
        today  = datetime.date.today().isoformat()
        doc_id = ""; sender_name = ""
        for entry in queue:
            if entry["route_id"] == route_id:
                entry["status"] = (ROUTE_STATUS["REJECTED"]
                                   if rejected else ROUTE_STATUS["REVIEWED"])
                entry["completed_date"]      = today
                entry["notes_from_reviewer"] = notes
                doc_id      = entry["doc_id"]
                sender_name = entry["assigned_by_name"]
                break
        if doc_id and sender_name:
            sender = {"name": sender_name, "email": ""}
            notif = self._build_notification(
                route_id=route_id, doc_id=doc_id, recipient=sender,
                notif_type=(NOTIFICATION_TYPE["REVIEW_REJECTED"]
                            if rejected else NOTIFICATION_TYPE["REVIEW_COMPLETE"]),
                doc_title="", doc_version="", sender=reviewer_name, notes=notes)
            notifs.append(notif)
        self.save_queue(queue)
        self.save_notifications(notifs)
        return {"ok": True}

    def recall_route(self, route_id, recalled_by):
        queue = self.load_queue()
        for entry in queue:
            if (entry["route_id"] == route_id and
                    entry["status"] == ROUTE_STATUS["PENDING"]):
                entry["status"] = ROUTE_STATUS["RECALLED"]
                entry["completed_date"] = datetime.date.today().isoformat()
                entry["notes_from_sender"] += f" | RECALLED by {recalled_by}"
        self.save_queue(queue)
        return {"ok": True}

    def broadcast_fyi(self, doc_id, doc_title, doc_version,
                      recipients, sender_name, notes=""):
        notifs = self.load_notifications()
        for r in recipients:
            notif = self._build_notification(
                route_id=f"FYI-{str(uuid.uuid4())[:6].upper()}",
                doc_id=doc_id, recipient=r,
                notif_type=NOTIFICATION_TYPE["FYI"],
                doc_title=doc_title, doc_version=doc_version,
                sender=sender_name, notes=notes)
            notifs.append(notif)
        self.save_notifications(notifs)
        return {"ok": True}

    def dismiss_notification(self, notif_id, user_name):
        notifs = self.load_notifications()
        for n in notifs:
            if n["notif_id"] == notif_id:
                n["dismissed"] = True
                n["read_date"] = datetime.datetime.now().isoformat()
        self.save_notifications(notifs)
        return {"ok": True}

    def get_pending_for_user(self, user_name, user_email=""):
        queue = self.load_queue()
        return [r for r in queue
                if r["status"] == ROUTE_STATUS["PENDING"] and
                (r["assigned_to_name"].lower() == user_name.lower() or
                 (user_email and
                  r["assigned_to_email"].lower() == user_email.lower()))]

    def get_notifications_for_user(self, user_name, user_email="",
                                   include_dismissed=False):
        notifs = self.load_notifications()
        result = []
        for n in notifs:
            name_match  = n["recipient_name"].lower() == user_name.lower()
            email_match = (user_email and
                           n["recipient_email"].lower() == user_email.lower())
            if name_match or email_match:
                if include_dismissed or not n.get("dismissed"):
                    result.append(n)
        return list(reversed(result))

    def get_queue_for_doc(self, doc_id):
        return [r for r in self.load_queue() if r["doc_id"] == doc_id]

    def get_all_pending(self):
        return [r for r in self.load_queue()
                if r["status"] == ROUTE_STATUS["PENDING"]]

    def get_overdue(self):
        today  = datetime.date.today()
        result = []
        for r in self.load_queue():
            if r["status"] == ROUTE_STATUS["PENDING"] and r.get("due_date"):
                try:
                    if datetime.date.fromisoformat(r["due_date"]) < today:
                        result.append(r)
                except Exception:
                    pass
        return result

    def get_stats(self):
        queue  = self.load_queue()
        notifs = self.load_notifications()
        today  = datetime.date.today()
        pending = [r for r in queue if r["status"] == "PENDING"]
        overdue = [r for r in pending if r.get("due_date") and
                   datetime.date.fromisoformat(r["due_date"]) < today]
        unread  = [n for n in notifs if not n.get("dismissed")]
        return {
            "total_routes":     len(queue),
            "pending_reviews":  len([r for r in pending
                                     if r["route_type"] == "REVIEW"]),
            "pending_approvals":len([r for r in pending
                                     if r["route_type"] == "APPROVAL"]),
            "overdue":          len(overdue),
            "unread_notifs":    len(unread),
        }

    # ── NOTIFICATION BUILDER ──────────────────────────────────────────────────

    def _build_notification(self, route_id, doc_id, recipient,
                            notif_type, doc_title, doc_version,
                            sender, notes="", due=""):
        subject, body = self._build_message(
            notif_type, doc_id, doc_title, doc_version, sender, notes, due)
        return {
            "notif_id":          f"N-{str(uuid.uuid4())[:8].upper()}",
            "route_id":          route_id,
            "doc_id":            doc_id,
            "recipient_name":    recipient.get("name", ""),
            "recipient_email":   recipient.get("email", ""),
            "notification_type": notif_type,
            "subject":           subject,
            "body":              body,
            "created_date":      datetime.datetime.now().isoformat(),
            "sent_date":         "",
            "sent_status":       "QUEUED",
            "sent_method":       "",
            "read_date":         "",
            "dismissed":         False
        }

    def _build_message(self, notif_type, doc_id, doc_title,
                       doc_version, sender, notes, due):
        base = doc_id
        if doc_title:   base += f" — {doc_title}"
        if doc_version: base += f" (Rev {doc_version})"
        templates = {
            "REVIEW_REQUESTED": (
                f"[QMS] Review Requested: {base}",
                f"You have been assigned to review:\n\n  {base}\n"
                f"  Submitted by: {sender}\n"
                f"  Due by: {due or 'See QMS App'}\n\n"
                f"{'Notes: ' + notes + chr(10) if notes else ''}"
                f"Open the QMS App or Word ribbon to begin your review."
            ),
            "APPROVAL_REQUESTED": (
                f"[QMS] Approval Required: {base}",
                f"A document requires your approval:\n\n  {base}\n"
                f"  Submitted by: {sender}\n\n"
                f"{'Notes: ' + notes + chr(10) if notes else ''}"
                f"Open the document and use Word ribbon → Approve."
            ),
            "REVIEW_COMPLETE": (
                f"[QMS] Review Complete: {base}",
                f"Review completed for: {doc_id}\n"
                f"  Reviewed by: {sender}\n\n"
                f"{'Notes: ' + notes + chr(10) if notes else ''}"
            ),
            "REVIEW_REJECTED": (
                f"[QMS] Review Returned — Action Required: {doc_id}",
                f"Document returned with comments:\n  {doc_id}\n"
                f"  Returned by: {sender}\n\n"
                f"{'Comments: ' + notes + chr(10) if notes else ''}"
            ),
            "DOCUMENT_APPROVED": (
                f"[QMS] Document Approved: {base}",
                f"Document approved and controlled:\n  {base}\n"
                f"  Approved by: {sender}\n"
            ),
            "FYI": (
                f"[QMS] For Your Information: {base}",
                f"Informational — no action required.\n\n  {base}\n"
                f"  From: {sender}\n\n"
                f"{'Notes: ' + notes if notes else ''}"
            ),
            "REVIEW_DUE_SOON": (
                f"[QMS] Periodic Review Due: {doc_id}",
                f"Document approaching annual review date:\n  {doc_id}\n"
                f"  Due: {due}\n"
            ),
        }
        default = (f"[QMS] {notif_type}: {doc_id}", f"{notif_type} for {doc_id}")
        return templates.get(notif_type, default)

    def _dispatch_notification(self, notif):
        """
        STUB — wire in email/Teams/SMS here.
        See User Guide Part 9 for implementation instructions.
        """
        pass

    def _dispatch_notifications(self, notifs):
        for n in notifs:
            self._dispatch_notification(n)
