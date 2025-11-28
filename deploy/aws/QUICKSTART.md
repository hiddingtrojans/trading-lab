# AWS Quick Start (5 minutes)

## Step 1: Create AWS Account
1. Go to https://aws.amazon.com/free
2. Sign up (requires credit card, but won't be charged for free tier)
3. New accounts get **12 months free** of t3.micro

## Step 2: Launch Instance (AWS Console)

1. Sign in to AWS Console
2. Go to **EC2** → **Launch Instance**
3. Configure:
   - **Name**: `trading-scanner`
   - **AMI**: Ubuntu 24.04 LTS ✓ Free tier eligible
   - **Instance type**: t3.micro ✓ Free tier eligible
   - **Key pair**: Create new → Download `.pem` file
   - **Network**: Allow SSH from "My IP"
4. Click **Launch Instance**
5. Wait 1-2 minutes for instance to start

## Step 3: Connect & Setup

```bash
# Make key file secure
chmod 400 your-key.pem

# Connect (replace with your instance IP from AWS console)
ssh -i your-key.pem ubuntu@YOUR_INSTANCE_IP

# Run setup script (takes ~5 minutes)
curl -sSL https://raw.githubusercontent.com/hiddingtrojans/trading-lab/main/deploy/aws/setup.sh | bash
```

## Step 4: Configure Credentials

```bash
# Set Telegram tokens
echo 'export TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN"' >> ~/.bashrc
echo 'export TELEGRAM_CHAT_ID="YOUR_CHAT_ID"' >> ~/.bashrc
source ~/.bashrc

# Configure IB Gateway
cp ~/ibc/config.ini.template ~/ibc/config.ini
nano ~/ibc/config.ini
# Add your IBKR username and password
```

## Step 5: Download IB Gateway

```bash
cd ~/ibgateway
wget https://download2.interactivebrokers.com/installers/ibgateway/stable-standalone/ibgateway-stable-standalone-linux-x64.sh
chmod +x ibgateway-stable-standalone-linux-x64.sh
./ibgateway-stable-standalone-linux-x64.sh -q
```

## Step 6: Start Everything

```bash
# Start scanner
~/start_scanner.sh

# Verify it's running
tail -f ~/scanner/logs/options_flow.log

# Enable cron jobs
crontab ~/scanner/deploy/aws/crontab.txt
```

## Step 7: Test

```bash
# Test Telegram alerts
cd ~/scanner
source venv/bin/activate
python -c "from alpha_lab.telegram_alerts import send_message; send_message('🎉 AWS Scanner Online!')"
```

You should receive a Telegram message!

---

## What Runs Automatically

| Time (ET) | What | Alert |
|-----------|------|-------|
| 9:00 AM | Daily signals | Trade ideas |
| 9:30 AM - 4 PM | Options flow (every 30min) | Unusual activity |
| Hourly | Position check | Stop/target alerts |
| 11 AM, 2 PM | Regime check | If regime changes |
| 4:30 PM | EOD Summary | Day recap |
| Friday 5 PM | Weekly report | Performance stats |

---

## Costs

**First 12 months**: FREE (750 hours/month of t3.micro)

**After free tier**: ~$10/month
- EC2: ~$8/month
- Storage: ~$1/month
- Data: ~$1/month

---

## Troubleshooting

**Can't connect via SSH?**
- Check security group allows your IP
- Verify instance is running
- Make sure .pem file permissions are `400`

**IB Gateway won't start?**
- Check credentials in `~/ibc/config.ini`
- Verify IBKR account has API enabled
- Try paper trading mode first

**No Telegram alerts?**
- Verify tokens: `echo $TELEGRAM_BOT_TOKEN`
- Test: `python -c "from alpha_lab.telegram_alerts import send_message; send_message('test')"`

