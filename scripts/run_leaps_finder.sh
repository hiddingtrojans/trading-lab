#!/bin/bash
# One-Click LEAPS Finder Script
# Double-click this file to run the complete LEAPS analysis

echo "🚀 SMART LEAPS FINDER - ONE-CLICK ANALYSIS"
echo "=========================================="
echo ""

# Navigate to scanner directory
cd "$(dirname "$0")"

# Activate virtual environment
echo "🔌 Activating environment..."
source venv/bin/activate

# Ensure API key is loaded
source ~/.zshrc

# Check if IBKR Gateway is running
echo "🔍 Checking IBKR Gateway connection..."
echo ""

# Run the smart LEAPS system
echo "🎯 Analyzing your universe for LEAPS opportunities..."
echo "📊 This will take about 2-3 minutes..."
echo ""

python complete_leaps_system.py --batch BCRX AIRO LUNR SRPT AMPX

echo ""
echo "✅ Analysis complete!"
echo "📁 Results saved to output/smart_leaps_results.csv"
echo "🤖 AI analysis included automatically - no copy/paste needed!"
echo ""
echo "🎯 Next steps:"
echo "   • Review the winners in the output above"
echo "   • Run individual analysis: python smart_leaps_system.py TICKER"
echo "   • When market opens: Verify LEAPS availability"
echo ""
echo "Press any key to exit..."
read -n 1
