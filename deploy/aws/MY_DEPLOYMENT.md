# Your AWS Deployment

## Instance Details

- **Instance ID**: i-080534024ab368273
- **Public IP**: 44.222.217.236 (changes on restart)
- **Region**: us-east-1
- **Instance Type**: t3.micro (free tier eligible)

## SSH Access

```bash
ssh -i ~/.ssh/scanner-key.pem ubuntu@98.92.17.204
```

---

## 🔐 IB Gateway (Docker) - WORKING ✅

IB Gateway runs via Docker with auto-restart.

**Check status:**
```bash
ssh -i ~/.ssh/scanner-key.pem ubuntu@98.92.17.204 "sudo docker ps"
ssh -i ~/.ssh/scanner-key.pem ubuntu@98.92.17.204 "sudo docker logs ibgateway --tail 20"
```

**Restart if needed:**
```bash
ssh -i ~/.ssh/scanner-key.pem ubuntu@98.92.17.204 "sudo docker restart ibgateway"
```

**API Ports:**
- 4001: Live trading
- 4002: Paper trading (currently active)
- 5900: VNC (for debugging)

---

## What's Running

### Automated Cron Jobs (all weekdays)

| Time (ET) | Task | Description |
|-----------|------|-------------|
| 8:30 AM | Daily Briefing | Market overview + top picks |
| 9:00 AM | Trade Scanner | Fresh signals with grading |
| 10 AM, 12 PM, 2 PM, 4 PM | Regime Check | Market condition alerts |
| 6:00 PM | Smart Money Scan | Insider trades |
| 6:05 PM | 13F Check | Hedge fund activity |

### Logs

```bash
# View logs
ssh -i ~/.ssh/scanner-key.pem ubuntu@98.92.17.204 "tail -50 ~/scanner/logs/briefing.log"
ssh -i ~/.ssh/scanner-key.pem ubuntu@98.92.17.204 "tail -50 ~/scanner/logs/trades.log"
```

## Management Commands

### Start/Stop Instance (save money when not using)

```bash
# Stop instance (no charges when stopped, except storage ~$0.80/month)
aws ec2 stop-instances --instance-ids i-080534024ab368273 --profile personal --region us-east-1

# Start instance
aws ec2 start-instances --instance-ids i-080534024ab368273 --profile personal --region us-east-1

# Check status
aws ec2 describe-instances --instance-ids i-080534024ab368273 --profile personal --region us-east-1 --query 'Reservations[0].Instances[0].State.Name'
```

**Note**: IP address changes when you stop/start. Get new IP with:
```bash
aws ec2 describe-instances --instance-ids i-080534024ab368273 --profile personal --region us-east-1 --query 'Reservations[0].Instances[0].PublicIpAddress' --output text
```

### Update Code

```bash
# From your Mac, in the scanner directory:
cd ~/Desktop/scanner
tar --exclude='leaps_env' --exclude='*.pyc' --exclude='__pycache__' --exclude='.git' -czf /tmp/scanner.tar.gz .
scp -i ~/.ssh/scanner-key.pem /tmp/scanner.tar.gz ubuntu@98.92.17.204:~
ssh -i ~/.ssh/scanner-key.pem ubuntu@98.92.17.204 "cd ~/scanner && tar -xzf ~/scanner.tar.gz"
```

### Run Manual Scan

```bash
# SSH in and run
ssh -i ~/.ssh/scanner-key.pem ubuntu@98.92.17.204
cd ~/scanner && source venv/bin/activate
export $(grep -v '^#' configs/telegram.env | xargs)

# Run daily briefing
python src/alpha_lab/daily_briefing.py

# Run trade scanner
python src/alpha_lab/trade_scanner.py

# Check Berkshire holdings
python src/alpha_lab/hedge_fund_tracker.py --fund "Berkshire Hathaway" --holdings
```

## Estimated Monthly Cost

| Resource | Cost |
|----------|------|
| t3.micro (24/7) | ~$8.50 |
| EBS Storage (8GB) | ~$0.80 |
| Data Transfer | ~$0.50 |
| **Total** | **~$10/month** |

**Tips to reduce cost:**
- Stop instance on weekends: `aws ec2 stop-instances ...`
- Use spot instances (not recommended for always-on)

## Terminate (Delete Everything)

```bash
# This will delete the instance permanently
aws ec2 terminate-instances --instance-ids i-080534024ab368273 --profile personal --region us-east-1

# Delete security group
aws ec2 delete-security-group --group-name scanner-sg --profile personal --region us-east-1

# Delete key pair
aws ec2 delete-key-pair --key-name scanner-key --profile personal --region us-east-1
rm ~/.ssh/scanner-key.pem
```

