#!/bin/bash
# Quick type checking script

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
