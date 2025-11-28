#!/bin/bash
# AWS EC2 Setup Script for Trading Scanner
# Run as: curl -sSL <url> | bash

set -e

echo "=========================================="
echo "  Trading Scanner - AWS Setup"
echo "=========================================="

# Update system
echo "[1/6] Updating system..."
sudo apt update && sudo apt upgrade -y

# Install dependencies
echo "[2/6] Installing dependencies..."
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    unzip \
    xvfb \
    libxrender1 \
    libxtst6 \
    libxi6 \
    openjdk-11-jre

# Clone repository
echo "[3/6] Cloning scanner repository..."
cd ~
if [ -d "scanner" ]; then
    cd scanner && git pull
else
    git clone https://github.com/hiddingtrojans/trading-lab.git scanner
fi
cd ~/scanner

# Create virtual environment
echo "[4/6] Setting up Python environment..."
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install ib_insync

# Setup directories
echo "[5/6] Creating directories..."
mkdir -p ~/ibgateway
mkdir -p ~/ibc
mkdir -p ~/scanner/logs
mkdir -p ~/scanner/data

# Download IBC (IB Controller)
echo "[6/6] Downloading IB Controller..."
cd ~/ibc
wget -q https://github.com/IbcAlpha/IBC/releases/download/3.18.0/IBCLinux-3.18.0.zip
unzip -o IBCLinux-3.18.0.zip
chmod +x scripts/*.sh

# Create IBC config template
cat > ~/ibc/config.ini.template << 'EOF'
# IBC Configuration
# Copy to config.ini and fill in your credentials

# Your IBKR credentials
IbLoginId=YOUR_IB_USERNAME
IbPassword=YOUR_IB_PASSWORD

# Trading mode: paper or live
TradingMode=paper

# Accept incoming API connections
AcceptIncomingConnectionAction=accept

# API settings
ExistingSessionDetectedAction=primary
AcceptNonBrokerageAccountWarning=yes

# Auto-restart settings
ClosedownAt=
EOF

# Create start script
cat > ~/start_scanner.sh << 'EOF'
#!/bin/bash
# Start IB Gateway and Scanner

# Start Xvfb (virtual display)
Xvfb :1 -screen 0 1024x768x24 &
export DISPLAY=:1

# Start IB Gateway via IBC
~/ibc/scripts/ibcstart.sh -g

# Wait for connection
sleep 30

# Start scanner in background
cd ~/scanner
source venv/bin/activate
nohup python src/alpha_lab/options_flow_scanner.py --daemon >> logs/options_flow.log 2>&1 &

echo "Scanner started. Check logs/options_flow.log"
EOF
chmod +x ~/start_scanner.sh

# Create systemd service (optional, for auto-start)
sudo tee /etc/systemd/system/trading-scanner.service > /dev/null << 'EOF'
[Unit]
Description=Trading Scanner with IB Gateway
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu
ExecStart=/home/ubuntu/start_scanner.sh
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Download IB Gateway:"
echo "   cd ~/ibgateway"
echo "   wget https://download2.interactivebrokers.com/installers/ibgateway/stable-standalone/ibgateway-stable-standalone-linux-x64.sh"
echo "   chmod +x ibgateway-stable-standalone-linux-x64.sh"
echo "   ./ibgateway-stable-standalone-linux-x64.sh -q"
echo ""
echo "2. Configure IBC:"
echo "   cp ~/ibc/config.ini.template ~/ibc/config.ini"
echo "   nano ~/ibc/config.ini  # Add your IBKR credentials"
echo ""
echo "3. Set Telegram tokens:"
echo "   echo 'export TELEGRAM_BOT_TOKEN=your_token' >> ~/.bashrc"
echo "   echo 'export TELEGRAM_CHAT_ID=your_chat_id' >> ~/.bashrc"
echo "   source ~/.bashrc"
echo ""
echo "4. Start scanner:"
echo "   ~/start_scanner.sh"
echo ""
echo "5. (Optional) Enable auto-start:"
echo "   sudo systemctl enable trading-scanner"
echo "   sudo systemctl start trading-scanner"
echo ""

