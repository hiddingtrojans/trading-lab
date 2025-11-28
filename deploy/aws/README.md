# AWS Deployment Guide

## Overview
Run the options flow scanner 24/7 on AWS Free Tier with IB Gateway.

## Architecture
```
┌─────────────────────────────────────────────┐
│  AWS EC2 (t3.micro - Free Tier)             │
│                                             │
│  ┌─────────────┐    ┌──────────────────┐    │
│  │ IB Gateway  │───▶│ Options Scanner  │    │
│  │ (headless)  │    │   (cron jobs)    │    │
│  └─────────────┘    └────────┬─────────┘    │
│                              │              │
└──────────────────────────────┼──────────────┘
                               │
                               ▼
                        ┌─────────────┐
                        │  Telegram   │
                        │   (you)     │
                        └─────────────┘
```

## Prerequisites
1. AWS account (new accounts get 12 months free tier)
2. Interactive Brokers account with API access enabled
3. Telegram bot token and chat ID

## Step 1: Launch EC2 Instance

1. Go to AWS Console → EC2 → Launch Instance
2. Settings:
   - **Name**: `trading-scanner`
   - **AMI**: Ubuntu 24.04 LTS (Free tier eligible)
   - **Instance type**: t3.micro (Free tier)
   - **Key pair**: Create new or use existing
   - **Security group**: Allow SSH (port 22) from your IP
   - **Storage**: 8 GB (default)

3. Click "Launch Instance"

## Step 2: Connect and Setup

```bash
# SSH into your instance
ssh -i your-key.pem ubuntu@<your-instance-ip>

# Run the setup script
curl -sSL https://raw.githubusercontent.com/hiddingtrojans/trading-lab/main/deploy/aws/setup.sh | bash
```

## Step 3: Configure IB Gateway

1. Download IB Gateway offline installer:
```bash
cd ~/ibgateway
wget https://download2.interactivebrokers.com/installers/ibgateway/stable-standalone/ibgateway-stable-standalone-linux-x64.sh
chmod +x ibgateway-stable-standalone-linux-x64.sh
./ibgateway-stable-standalone-linux-x64.sh -q
```

2. Configure IBC (IB Controller) for automated login:
```bash
nano ~/ibc/config.ini
# Set your credentials (see config.ini.template)
```

3. Start IB Gateway:
```bash
~/ibc/scripts/ibcstart.sh
```

## Step 4: Set Environment Variables

```bash
# Add to ~/.bashrc
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
export IB_ACCOUNT="your_ib_account"
```

## Step 5: Start Scanner

```bash
# One-time test
cd ~/scanner
python src/alpha_lab/options_flow_scanner.py --test

# Enable cron jobs
crontab ~/scanner/deploy/aws/crontab.txt
```

## Monitoring

Check scanner logs:
```bash
tail -f ~/scanner/logs/options_flow.log
```

Check IB Gateway status:
```bash
~/ibc/scripts/ibcstatus.sh
```

## Costs

| Resource | Free Tier | After Free Tier |
|----------|-----------|-----------------|
| EC2 t3.micro | 750 hrs/month | ~$8/month |
| EBS 8GB | 30 GB free | ~$0.80/month |
| Data transfer | 100 GB/month | ~$0.09/GB |

**Total after free tier: ~$10/month**

## Security Notes

1. Never commit credentials to git
2. Use AWS Secrets Manager for production
3. Restrict security group to your IP only
4. Enable 2FA on your AWS account
5. Use a paper trading account first!

## Troubleshooting

### IB Gateway won't connect
- Check your IBKR account has API enabled
- Verify port 4001 is open in IB Gateway settings
- Check IBC logs: `tail ~/ibc/logs/*.log`

### Scanner not sending alerts
- Verify Telegram tokens: `echo $TELEGRAM_BOT_TOKEN`
- Test manually: `python -c "from alpha_lab.telegram_alerts import send_message; send_message('test')"`

### Instance stopped
- Free tier t3.micro may stop if you exceed limits
- Set up CloudWatch alarm to notify you

