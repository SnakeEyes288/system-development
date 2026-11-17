#!/usr/bin/env bash
# Universal System Development Skill - Auto-Installer for macOS / Linux
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================================="
echo " 🚀 System Development Skill - Multi-Agent Installer"
echo "=========================================================="

TARGETS=(
  "$HOME/.gemini/config/skills/system-development"
  "$HOME/.agents/skills/system-development"
  "$HOME/.claude/skills/system-development"
  "$HOME/.codex/skills/system-development"
)

ITEMS=("SKILL.md" "README.md" "references" "scripts" "tests")

for dest in "${TARGETS[@]}"; do
  mkdir -p "$dest"
  for item in "${ITEMS[@]}"; do
    if [ -e "$SCRIPT_DIR/$item" ]; then
      cp -R "$SCRIPT_DIR/$item" "$dest/"
    fi
  done
  echo " [OK] Installed successfully to: $dest"
done

echo ""
echo "🎉 Installation complete! Available to your AI Agents."
