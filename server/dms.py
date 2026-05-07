#!/usr/bin/env python3
"""QMS DMS CLI controller for common API operations."""

from __future__ import annotations

import argparse
import json
import os
import sys

import requests


API_BASE = os.environ.get("QMS_API_BASE", "http://127.0.0.1:5151")


def _request(method: str, endpoint: str, payload=None):
    url = f"{API_BASE}{endpoint}"
    resp = requests.request(method=method, url=url, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def cmd_list(_args):
    data = _request("GET", "/documents")
    print(json.dumps(data, indent=2))


def cmd_stats(_args):
    data = _request("GET", "/stats")
    print(json.dumps(data, indent=2))


def cmd_new(args):
    payload = {
        "doc_type": args.doc_type,
        "title": args.title,
        "owner": args.owner,
    }
    data = _request("POST", "/documents/new", payload)
    print(json.dumps(data, indent=2))


def cmd_import(args):
    payload = {
        "file_path": args.file_path,
        "doc_type": args.doc_type,
        "title": args.title,
        "owner": args.owner,
    }
    data = _request("POST", "/documents/import", payload)
    print(json.dumps(data, indent=2))


def cmd_promote(args):
    payload = {"action": args.action, "user": args.user}
    data = _request("POST", f"/documents/{args.doc_id}/promote", payload)
    print(json.dumps(data, indent=2))


def main():
    parser = argparse.ArgumentParser(description="QMS DMS CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List documents")
    p_list.set_defaults(func=cmd_list)

    p_stats = sub.add_parser("stats", help="Show summary stats")
    p_stats.set_defaults(func=cmd_stats)

    p_new = sub.add_parser("new", help="Create a new document")
    p_new.add_argument("doc_type", help="Document type, e.g. SOP")
    p_new.add_argument("title", help="Document title")
    p_new.add_argument("--owner", default="", help="Document owner")
    p_new.set_defaults(func=cmd_new)

    p_import = sub.add_parser("import", help="Import existing file")
    p_import.add_argument("file_path", help="Path to source file")
    p_import.add_argument("--type", dest="doc_type", required=True, help="Document type")
    p_import.add_argument("--title", required=True, help="Document title")
    p_import.add_argument("--owner", default="", help="Document owner")
    p_import.set_defaults(func=cmd_import)

    p_promote = sub.add_parser("promote", help="Promote lifecycle status")
    p_promote.add_argument("doc_id", help="Document ID")
    p_promote.add_argument("action", help="Promotion action")
    p_promote.add_argument("--user", default="", help="Acting user")
    p_promote.set_defaults(func=cmd_promote)

    args = parser.parse_args()
    try:
        args.func(args)
    except requests.HTTPError as exc:
        body = ""
        if exc.response is not None:
            body = exc.response.text
        print(f"HTTP error: {exc}\n{body}", file=sys.stderr)
        sys.exit(1)
    except requests.RequestException as exc:
        print(f"Request error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
