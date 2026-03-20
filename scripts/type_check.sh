#!/bin/bash
# Quick type checking script

# Set Django environment variables for type checking
export DJANGO_SETTINGS_MODULE=progress_rpg.settings.dev
export SECRET_KEY=${SECRET_KEY:-"type-checking-secret-key"}

echo "🔍 Running mypy type checker..."
echo ""

if [ -z "$1" ]; then
    echo "Checking entire project..."
    mypy . --config-file=mypy.ini
else
    echo "Checking: $1"
    mypy "$1" --config-file=mypy.ini
fi

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "✅ Type checking passed!"
else
    echo ""
    echo "❌ Type checking found issues. Review output above."
fi

exit $exit_code
