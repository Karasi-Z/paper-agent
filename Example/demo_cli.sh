#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="${PAPER_AGENT_DATA_DIR:-$(pwd)/.demo_data}"
TMP_TEXT=""

cleanup() {
  if [[ -n "${TMP_TEXT}" && -f "${TMP_TEXT}" ]]; then
    rm -f "${TMP_TEXT}"
  fi
}

trap cleanup EXIT

echo "[1/5] Create project"
PROJECT_JSON=$(python3 -m paper_agent --data-dir "$DATA_DIR" create-project \
  --name "Scientific RAG Demo" \
  --question "What are the main technical routes of scientific literature agents?")
echo "$PROJECT_JSON"

PROJECT_ID=$(printf '%s' "$PROJECT_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["project_id"])')

echo "[2/5] Import a local sample paper"
TMP_TEXT="$(mktemp)"
cat > "$TMP_TEXT" <<'EOF'
Scientific literature agents combine lexical retrieval, dense retrieval, reranking, and evidence-grounded synthesis.
EOF
python3 -m paper_agent --data-dir "$DATA_DIR" import-text --project-id "$PROJECT_ID" --title "Local Demo Paper" --file "$TMP_TEXT"

echo "[3/5] Build index"
python3 -m paper_agent --data-dir "$DATA_DIR" build-index --project-id "$PROJECT_ID"

echo "[4/5] Ask a question"
python3 -m paper_agent --data-dir "$DATA_DIR" ask --project-id "$PROJECT_ID" --query "Summarize the technical routes"

echo "[5/5] Export markdown"
python3 -m paper_agent --data-dir "$DATA_DIR" export --project-id "$PROJECT_ID" --format markdown
