.PHONY: help setup env dev ping stats docs roster test-new-doc test-lifecycle register logs reset clean

# Default target
help:
	@echo "QMS DMS Development Commands"
	@echo "============================"
	@echo ""
	@echo "Setup:"
	@echo "  make setup          Install Python packages and npm dependencies"
	@echo "  make env            Create TEST_QMS folder with sample data"
	@echo "  make reset          Wipe TEST_QMS and recreate from scratch"
	@echo ""
	@echo "Development:"
	@echo "  make dev            Start server with auto-reload (port 5151)"
	@echo "  make ping           Health check"
	@echo ""
	@echo "Data inspection:"
	@echo "  make stats          Show document and CR statistics"
	@echo "  make docs           List all documents"
	@echo "  make roster         Show team members"
	@echo "  make register       Pretty-print document register"
	@echo "  make logs           Show audit trail"
	@echo ""
	@echo "Testing:"
	@echo "  make test-new-doc   Create a test document"
	@echo "  make test-lifecycle Run Draft→Review→Approve cycle"
	@echo "  make test-all       Run all tests"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean          Remove Python cache and temp files"
	@echo ""

# ── Setup ────────────────────────────────────────────────────────────────────

setup:
	@echo "Installing Python packages..."
	pip install -q -r requirements.txt
	@echo "Installing docx npm package..."
	npm install -g docx 2>/dev/null || echo "npm not available, skipping docx"
	@echo "✓ Setup complete"

env:
	@echo "Creating test environment..."
	python setup_test_env.py

reset:
	@echo "Resetting test environment..."
	rm -rf TEST_QMS
	python setup_test_env.py

# ── Development ──────────────────────────────────────────────────────────────

dev:
	@echo "Starting QMS DMS Server with auto-reload..."
	@echo "Server will restart automatically when you save Python files."
	@echo "Press Ctrl+C to stop."
	cd server && python dms_server.py

# ── API Testing ──────────────────────────────────────────────────────────────

ping:
	@curl -s http://localhost:5151/ping | python -m json.tool

stats:
	@curl -s http://localhost:5151/stats | python -m json.tool

docs:
	@curl -s http://localhost:5151/documents | python -m json.tool

roster:
	@curl -s http://localhost:5151/roster | python -m json.tool

register:
	@echo "Document Register:"
	@echo "=================="
	@curl -s http://localhost:5151/documents | python -c "import sys, json; docs = json.load(sys.stdin); print('\n'.join([f\"{d['doc_id']:15} {d['status']:18} {d['type']:25} {d['title'][:40]}\" for d in docs]))"

logs:
	@curl -s http://localhost:5151/audit-log | python -m json.tool

# ── Testing ──────────────────────────────────────────────────────────────────

test-new-doc:
	@echo "Creating test document..."
	@curl -s -X POST http://localhost:5151/documents/new \
		-H "Content-Type: application/json" \
		-d '{"doc_type":"SOP","title":"Test Procedure","owner":"Dev User"}' \
		| python -m json.tool

test-lifecycle:
	@echo "Testing document lifecycle..."
	@echo ""
	@echo "1. Creating DRAFT document..."
	@curl -s -X POST http://localhost:5151/documents/new \
		-H "Content-Type: application/json" \
		-d '{"doc_type":"SOP","title":"Lifecycle Test","owner":"Dev User"}' \
		> /tmp/qms_test_doc.json
	@cat /tmp/qms_test_doc.json | python -c "import sys, json; d=json.load(sys.stdin); print(f\"   Created: {d.get('doc',{}).get('doc_id')} - {d.get('doc',{}).get('status')}\")"
	@echo ""
	@echo "2. Submitting for review..."
	@DOC_ID=$$(cat /tmp/qms_test_doc.json | python -c "import sys, json; print(json.load(sys.stdin).get('doc',{}).get('doc_id',''))"); \
		curl -s -X POST http://localhost:5151/routing/submit-review \
		-H "Content-Type: application/json" \
		-d "{\"doc_id\":\"$$DOC_ID\",\"reviewers\":[{\"name\":\"Tech Reviewer\",\"email\":\"tech@acmemedical.com\"}],\"user\":\"Dev User\"}" \
		| python -c "import sys, json; print(f\"   Status: {json.load(sys.stdin).get('ok')}\")"
	@echo ""
	@echo "3. Completing review..."
	@ROUTE_ID=$$(curl -s http://localhost:5151/routing/queue | python -c "import sys, json; q=json.load(sys.stdin); print(q[-1]['route_id'] if q else '')"); \
		curl -s -X POST http://localhost:5151/routing/complete-review \
		-H "Content-Type: application/json" \
		-d "{\"route_id\":\"$$ROUTE_ID\",\"reviewer_name\":\"Tech Reviewer\",\"notes\":\"Approved\",\"rejected\":false}" \
		| python -c "import sys, json; print(f\"   Review complete: {json.load(sys.stdin).get('ok')}\")"
	@echo ""
	@echo "✓ Lifecycle test complete"

test-all: test-new-doc test-lifecycle
	@echo ""
	@echo "✓ All tests complete"

# ── Cleanup ──────────────────────────────────────────────────────────────────

clean:
	@echo "Cleaning Python cache..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@echo "✓ Clean complete"
