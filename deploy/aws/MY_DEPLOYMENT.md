# Your AWS Deployment

## Instance Details

- **Instance ID**: i-080534024ab368273
- **Public IP**: 3.95.27.222 (changes on restart)
- **Region**: us-east-1
- **Instance Type**: t3.micro (free tier eligible)

## SSH Access

```bash
ssh -i ~/.ssh/scanner-key.pem ubuntu@3.95.27.222
```

---

## 🔐 IB Gateway (Docker) - WORKING ✅

IB Gateway runs via Docker with `--net=host` (required for API socket).

**Start IB Gateway:**
```bash
ssh -i ~/.ssh/scanner-key.pem ubuntu@3.95.27.222 "sudo docker run -d --name ibgateway \
  --net=host \
  -e TRADING_MODE=paper \
  -e TWS_USERID='racedomilla' \
  -e TWS_PASSWORD='R@ylCp4U_7X7aAM' \
  -e TWS_ACCEPT_INCOMING=accept \
  -e VNC_SERVER_PASSWORD=scanner123 \
  ghcr.io/gnzsnz/ib-gateway:latest"
```

**Check status:**
```bash
ssh -i ~/.ssh/scanner-key.pem ubuntu@3.95.27.222 "sudo docker ps"
ssh -i ~/.ssh/scanner-key.pem ubuntu@3.95.27.222 "ss -tlnp | grep 4002"
```

**API Port:** 4002 (paper trading)
**VNC Port:** 5900 (for debugging)

---

## What's Running

### Automated Cron Jobs (all weekdays)

| Time (ET) | Task | Description |
|-----------|------|-------------|
| 8:30 AM | Morning Scan | Market regime + unusual activity |
| 10 AM, 12 PM, 2 PM | **Options Flow** | Detect smart money (NEW!) |
| 10 AM, 12 PM, 2 PM, 4 PM | Regime Check | Market condition alerts |
| 6:00 PM | Smart Money Scan | Insider trades |
| 6:05 PM | 13F Check | Hedge fund activity |

### Options Flow Scanner (NEW!)

Detects:
- Large premium trades (>$50K)
- High volume/OI ratio (new positions)
- Far OTM sweeps (speculative bets)

This is what Unusual Whales charges $40/mo for.

### Logs

```bash
# View logs
ssh -i ~/.ssh/scanner-key.pem ubuntu@3.95.27.222 "tail -50 ~/scanner/logs/morning.log"
ssh -i ~/.ssh/scanner-key.pem ubuntu@3.95.27.222 "tail -50 ~/scanner/logs/options_flow.log"
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

### Run Manual Scan

```bash
# SSH in and run
ssh -i ~/.ssh/scanner-key.pem ubuntu@3.95.27.222
cd ~/scanner && source venv/bin/activate
source configs/telegram.env

# Run morning scan
python src/alpha_lab/morning_scan.py

# Run options flow scanner
python src/alpha_lab/options_flow_scanner.py

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
