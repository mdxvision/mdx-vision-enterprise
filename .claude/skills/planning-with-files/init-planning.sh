#!/bin/bash
# Initialize planning files for a new task
# Usage: ./init-planning.sh "Task Name"

TASK_NAME="${1:-New Task}"
DATE=$(date +"%Y-%m-%d")
TEMPLATE_DIR="$(dirname "$0")/templates"

echo "📋 Creating planning files for: $TASK_NAME"
echo "─────────────────────────────────────────"

# Create task_plan.md
if [ -f "task_plan.md" ]; then
    echo "⚠️  task_plan.md already exists, skipping..."
else
    sed -e "s/\[TASK_NAME\]/$TASK_NAME/g" \
        -e "s/\[DATE\]/$DATE/g" \
        "$TEMPLATE_DIR/task_plan.md" > task_plan.md
    echo "✅ Created task_plan.md"
fi

# Create findings.md
if [ -f "findings.md" ]; then
    echo "⚠️  findings.md already exists, skipping..."
else
    sed -e "s/\[TASK_NAME\]/$TASK_NAME/g" \
        -e "s/\[DATE\]/$DATE/g" \
        "$TEMPLATE_DIR/findings.md" > findings.md
    echo "✅ Created findings.md"
fi

# Create progress.md
if [ -f "progress.md" ]; then
    echo "⚠️  progress.md already exists, skipping..."
else
    sed -e "s/\[TASK_NAME\]/$TASK_NAME/g" \
        -e "s/\[DATE\]/$DATE/g" \
        "$TEMPLATE_DIR/progress.md" > progress.md
    echo "✅ Created progress.md"
fi

echo "─────────────────────────────────────────"
echo "📁 Planning files ready!"
echo ""
echo "Next steps:"
echo "  1. Edit task_plan.md - Define your phases"
echo "  2. Start research - Update findings.md"
echo "  3. Track progress - Update progress.md"
echo ""
echo "Remember: 2-Action Rule - Update findings after every 2 browse/search ops!"
