#!/bin/bash
#
# RESEARCH PLATFORM CRON SETUP
# ============================
#
# Run this on AWS to set up scheduled scans:
# 1. Weekly comprehensive scan (Sunday 10 PM)
# 2. Daily watchlist alerts (6 PM)
#
# Usage:
#   chmod +x setup_research_crons.sh
#   ./setup_research_crons.sh
#

SCANNER_DIR="/home/ubuntu/scanner"
PYTHON="/home/ubuntu/scanner/venv/bin/python"
LOG_DIR="/home/ubuntu/scanner/logs"

# Create logs directory
mkdir -p $LOG_DIR

echo "Setting up Research Platform crons..."

# Create the crontab entries
cat << 'EOF' > /tmp/research_crons
# ═══════════════════════════════════════════════════════════
# RESEARCH PLATFORM CRONS
# ═══════════════════════════════════════════════════════════

# WEEKLY COMPREHENSIVE SCAN (Sunday 10 PM EST)
# Scans ALL 11,552 US stocks, saves to database
# Compares to last week to find IMPROVEMENTS
# Sends Telegram alert with discoveries
0 22 * * 0 cd /home/ubuntu/scanner && /home/ubuntu/scanner/venv/bin/python -m src.research.alerts --weekly-scan >> /home/ubuntu/scanner/logs/weekly_scan.log 2>&1

# DAILY WATCHLIST ALERTS (6 PM EST)
# Checks YOUR watchlist only:
# - Price targets hit
# - Upcoming earnings
# - Significant moves
0 18 * * 1-5 cd /home/ubuntu/scanner && /home/ubuntu/scanner/venv/bin/python -m src.research.alerts >> /home/ubuntu/scanner/logs/daily_alerts.log 2>&1

# WEEKLY DIGEST (Sunday 6 PM EST)
# Summary of your watchlist status
0 18 * * 0 cd /home/ubuntu/scanner && /home/ubuntu/scanner/venv/bin/python -m src.research.alerts --weekly >> /home/ubuntu/scanner/logs/weekly_digest.log 2>&1

# ═══════════════════════════════════════════════════════════
EOF

# Install crontab
crontab /tmp/research_crons

echo "✅ Crons installed!"
echo ""
echo "Schedule:"
echo "  📊 Weekly Scan:    Sunday 10 PM  (full universe + improvements)"
echo "  📬 Daily Alerts:   6 PM Mon-Fri  (watchlist only)"
echo "  📋 Weekly Digest:  Sunday 6 PM   (summary)"
echo ""
echo "View current crons: crontab -l"
echo "View logs: tail -f $LOG_DIR/*.log"

