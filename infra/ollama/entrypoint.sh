#!/bin/bash
# Pull configured model on first start, then run server.
# Model: ${OLLAMA_MODEL:-llama3.3:8b-instruct-q4_K_M} — see RESEARCH §4 for choice rationale.

set -e

MODEL="${OLLAMA_MODEL:-llama3.3:8b-instruct-q4_K_M}"

# Start ollama serve in background to allow `ollama pull` to communicate with it.
ollama serve &
SERVE_PID=$!

# Wait for server to be ready
echo "Waiting for ollama daemon..."
until ollama list >/dev/null 2>&1; do
  sleep 1
done

# Pull model if not already present (cached in /root/.ollama volume)
if ! ollama list | grep -q "$(echo "$MODEL" | cut -d: -f1)"; then
  echo "Pulling model: $MODEL"
  ollama pull "$MODEL"
else
  echo "Model $MODEL already cached"
fi

# Bring server to foreground
wait "$SERVE_PID"
