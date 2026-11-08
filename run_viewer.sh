#!/usr/bin/env bash
# =============================================================================
# LungPair 3D Molecular Viewer Launcher (AgentVerse 2026)
# =============================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

HTML_FILE="$ROOT_DIR/visual/dist/index.html"

# If pre-built HTML is missing, build it if npm is available
if [ ! -f "$HTML_FILE" ]; then
    if command -v npm >/dev/null 2>&1; then
        echo "Building 3D visual app..."
        (cd visual && npm install --silent && npm run build)
    else
        echo "Error: visual/dist/index.html not found and npm is not installed."
        exit 1
    fi
fi

echo "Opening LungPair 3D Molecular & Synergy Viewer in your browser..."

# Open in default browser across platforms
if [[ "$OSTYPE" == "darwin"* ]]; then
    open "$HTML_FILE"
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$HTML_FILE"
elif command -v wslview >/dev/null 2>&1; then
    wslview "$HTML_FILE"
else
    echo "Viewer ready at: file://$HTML_FILE"
    echo "Please open this file in your web browser."
fi
