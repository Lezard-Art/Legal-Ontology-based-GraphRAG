#!/bin/bash
# Start the Contract Ontology Database server
cd "$(dirname "$0")"
export PATH="$PATH:$HOME/.local/bin"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "Starting Contract Ontology Database on http://localhost:8000"
echo "API docs at http://localhost:8000/docs"
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
