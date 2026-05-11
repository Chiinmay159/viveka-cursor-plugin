#!/usr/bin/env bash
# Viveka OS — Cursor installer
# Run from your project directory:
#   bash /path/to/viveka-os/platforms/cursor/install.sh

set -euo pipefail

VIVEKA_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PROJECT_DIR="${1:-$(pwd)}"

echo "Installing Viveka OS for Cursor in $PROJECT_DIR"

if [ -f "$PROJECT_DIR/.cursorrules" ]; then
    if grep -q "GRASPING" "$PROJECT_DIR/.cursorrules"; then
        echo "  .cursorrules already contains Viveka."
    else
        echo "" >> "$PROJECT_DIR/.cursorrules"
        cat "$VIVEKA_ROOT/CLAUDE.md" >> "$PROJECT_DIR/.cursorrules"
        echo "  ✓ .cursorrules (appended)"
    fi
else
    cp "$VIVEKA_ROOT/CLAUDE.md" "$PROJECT_DIR/.cursorrules"
    echo "  ✓ .cursorrules"
fi

mkdir -p "$PROJECT_DIR/.cursor/skills"
for skill_dir in "$VIVEKA_ROOT"/skills/*/; do
    skill_name=$(basename "$skill_dir")
    mkdir -p "$PROJECT_DIR/.cursor/skills/${skill_name}"
    cp "$skill_dir/SKILL.md" "$PROJECT_DIR/.cursor/skills/${skill_name}/SKILL.md"
    echo "  ✓ .cursor/skills/${skill_name}/SKILL.md"
done

mkdir -p "$PROJECT_DIR/.viveka/memory"
echo "  ✓ .viveka/memory/"
echo ""
echo "Done. Viveka OS is active in Cursor."
