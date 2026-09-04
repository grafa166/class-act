#!/bin/bash
# Double-click this file to start Class Act.
# It opens in your web browser. Close this black window to stop the app.

cd "$(dirname "$0")" || exit 1

clear
echo "======================================"
echo "  Class Act — Worksheet Generator"
echo "======================================"
echo

if [ ! -x ".venv/bin/streamlit" ]; then
  echo "The app isn't set up in this folder yet."
  echo "Ask Claude to reinstall it, or run:  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  echo
  read -r -p "Press Return to close..."
  exit 1
fi

if [ ! -f ".env" ]; then
  echo "The Anthropic key file (.env) is missing, so worksheets can't be generated."
  echo "Ask Claude to recreate it."
  echo
  read -r -p "Press Return to close..."
  exit 1
fi

echo "Starting up — your browser will open in a few seconds."
echo
echo "Leave this window open while you work."
echo "To stop the app, close this window."
echo

# --server.headless false makes Streamlit open the browser itself.
./.venv/bin/streamlit run app.py \
  --server.port 8501 \
  --server.headless false \
  --browser.gatherUsageStats false

echo
echo "Class Act has stopped."
read -r -p "Press Return to close this window..."
