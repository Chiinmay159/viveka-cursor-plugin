#!/usr/bin/env bash
# Viveka — Cursor installer
# Run from your project directory:
#   bash /path/to/viveka-cursor-plugin/platforms/cursor/install.sh

set -euo pipefail

VIVEKA_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PROJECT_DIR="${1:-$(pwd)}"

echo "Installing Viveka for Cursor in $PROJECT_DIR"

# Install kernel rule (modern .cursor/rules/ convention)
mkdir -p "$PROJECT_DIR/.cursor/rules"
cp "$VIVEKA_ROOT/rules/viveka-framework.mdc" "$PROJECT_DIR/.cursor/rules/viveka-framework.mdc"
echo "  ✓ .cursor/rules/viveka-framework.mdc"

# Migrate legacy .cursorrules if it contains old Viveka content
if [ -f "$PROJECT_DIR/.cursorrules" ] && grep -q "GRASPING" "$PROJECT_DIR/.cursorrules"; then
    echo "  ⚠ Legacy .cursorrules with Viveka detected — the .mdc rule replaces it."
    echo "    Remove the Viveka content from .cursorrules to avoid duplication."
fi

# Install skills (loaded on demand via slash commands)
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
echo "Done. Viveka is active in Cursor."
echo "  Kernel loads automatically (~1.1K tokens)."
echo "  Skills load on demand via /viveka-<name> (~11K tokens available)."
