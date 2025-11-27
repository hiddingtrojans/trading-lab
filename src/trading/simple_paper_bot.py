#!/usr/bin/env python3
"""
Simple Paper Trading Bot with Working Dashboard
==============================================

A simplified but fully functional paper trading bot with a working dashboard.
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from .day_trading_bot import DayTradingBot, CONFIG
from .improved_options_scanner import ImprovedOptionsScanner
from dashboard.simple_dashboard import SimpleTradingDashboard, start_simple_dashboard
import threading
import time
from datetime import datetime

class SimplePaperTradingBot(DayTradingBot):
    """Simplified paper trading bot with working dashboard."""
    
    def __init__(self, config):
        super().__init__(config)
        
        # Initialize improved options scanner
        self.options_scanner = ImprovedOptionsScanner(self.ib, self.config)
        
        # Initialize simple dashboard
        self.dashboard = SimpleTradingDashboard(self)
        
        # Override for paper trading safety
        self.config['IB_PORT'] = 4002  # Force paper trading
        self.config['MAX_DAILY_LOSS'] = 10000.0  # Higher limit for paper trading
        self.config['MAX_POSITION_PCT'] = 5.0  # Smaller positions for testing
        
        self.logger.info("📊 Simple dashboard integration enabled")
        self.logger.info("🛡️ Paper trading mode: SAFE TESTING ONLY")
    
    async def execute_long_entry(self, symbol: str, current_price: float) -> bool:
        """Execute long entry with dashboard tracking."""
        success = await super().execute_long_entry(symbol, current_price)
        
        if success:
            # Update dashboard with new position
            position = self.positions[symbol]
            trade_data = {
                'action': 'ENTRY',
                'symbol': symbol,
                'shares': position['shares'],
                'price': position['entry_price'],
                'pnl': 0,  # No P&L on entry
                'timestamp': position['entry_time']
            }
            self.dashboard.update_trade_history(trade_data)
            self.logger.info(f"📊 Dashboard updated with new position: {symbol}")
        
        return success
    
    async def execute_exit(self, symbol: str, current_price: float, reason: str):
        """Execute exit with dashboard tracking."""
        if symbol not in self.positions:
            return
        
        # Calculate P&L before exit
        position = self.positions[symbol]
        pnl = (current_price - position['entry_price']) * position['shares']
        
        # Execute the exit
        await super().execute_exit(symbol, current_price, reason)
        
        # Update dashboard with exit
        trade_data = {
            'action': 'EXIT',
            'symbol': symbol,
            'shares': position['shares'],
            'price': current_price,
            'pnl': pnl,
            'reason': reason,
            'timestamp': datetime.now()
        }
        self.dashboard.update_trade_history(trade_data)
        self.logger.info(f"📊 Dashboard updated with exit: {symbol} - P&L: ${pnl:.2f}")
    
    async def sync_positions_from_ib(self):
        """Sync positions from IB Gateway to bot's internal tracking."""
        try:
            # Get positions from IB Gateway
            positions = self.ib.positions()
            
            for position in positions:
                if position.position > 0:  # Only long positions
                    symbol = position.contract.symbol
                    if symbol not in self.positions:
                        # Add position to bot's tracking
                        self.positions[symbol] = {
                            'shares': position.position,
                            'entry_price': position.avgCost,
                            'entry_time': datetime.now(),
                            'stop_price': position.avgCost * 0.95,  # 5% stop loss
                            'take_profit_price': position.avgCost * 1.10  # 10% take profit
                        }
                        
                        # Add to dashboard trade history
                        trade_data = {
                            'action': 'ENTRY',
                            'symbol': symbol,
                            'shares': position.position,
                            'price': position.avgCost,
                            'pnl': 0,
                            'timestamp': datetime.now()
                        }
                        self.dashboard.update_trade_history(trade_data)
                        self.logger.info(f"📊 Synced existing position: {symbol} - {position.position} shares @ ${position.avgCost:.2f}")
            
        except Exception as e:
            self.logger.error(f"⚠️ Error syncing positions: {e}")

    async def run_trading_session_with_dashboard(self):
        """Run trading session with simple dashboard in background."""
        # Start dashboard in separate thread
        dashboard_thread = threading.Thread(
            target=lambda: start_simple_dashboard(self.dashboard, host='127.0.0.1', port=5000),
            daemon=True
        )
        dashboard_thread.start()
        
        self.logger.info("🌐 Simple dashboard started at http://127.0.0.1:5000")
        self.logger.info("📊 Monitor your bot's performance in real-time!")
        
        # Wait a moment for dashboard to start
        await asyncio.sleep(2)
        
        # Connect to IB Gateway first
        self.logger.info("🔌 Connecting to IB Gateway...")
        await self.connect_to_ib()
        
        if self.ib.isConnected():
            self.logger.info("✅ Connected to IB Gateway successfully")
            
            # Sync existing positions from IB Gateway
            await self.sync_positions_from_ib()
            
            # Start position monitoring task
            asyncio.create_task(self.monitor_positions_for_dashboard())
            
            # Run a simple trading loop
            await self.run_simple_trading_loop()
        else:
            self.logger.error("❌ Failed to connect to IB Gateway")
            return
    
    async def monitor_positions_for_dashboard(self):
        """Monitor positions and update dashboard with live P&L."""
        while True:
            try:
                # Get portfolio from IB Gateway
                portfolio = self.ib.portfolio()
                
                for item in portfolio:
                    if item.position > 0:  # Long positions only
                        symbol = item.contract.symbol
                        current_pnl = item.unrealizedPNL
                        
                        # Update dashboard with live P&L
                        if symbol in self.positions:
                            # Update the position's current P&L
                            self.positions[symbol]['current_pnl'] = current_pnl
                            self.positions[symbol]['current_price'] = item.marketPrice
                            
                            # Send live update to dashboard
                            self.dashboard.update_live_pnl(symbol, current_pnl, item.marketPrice)
                
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except Exception as e:
                self.logger.error(f"⚠️ Error monitoring positions: {e}")
                await asyncio.sleep(10)
    
    async def run_simple_trading_loop(self):
        """Run the actual VWAP day trading strategy with gap-up scanning."""
        self.logger.info("🔄 Starting VWAP day trading strategy...")
        self.logger.info("📊 Strategy: Scan for 2-3% gap-ups, enter on VWAP test")
        
        try:
            # Check if we're in pre-market or market hours
            if self.is_premarket_hours():
                self.logger.info("🌅 PRE-MARKET: Scanning for gap-up candidates...")
                candidates = await self.scan_gap_up_candidates()
                if candidates:
                    self.logger.info(f"🎯 Found {len(candidates)} gap-up candidates:")
                    for candidate in candidates[:5]:  # Show top 5
                        self.logger.info(f"   {candidate['symbol']}: {candidate['gap_pct']:.1f}% gap @ ${candidate['current_price']:.2f}")
                else:
                    self.logger.info("📊 No gap-up candidates found")
            
            # Run the actual trading session with VWAP strategy
            await self.run_trading_session()
                
        except KeyboardInterrupt:
            self.logger.info("⏹️ Trading loop stopped by user")
        except Exception as e:
            self.logger.error(f"❌ Trading loop error: {e}")

def print_simple_paper_trading_info():
    """Print simple paper trading setup information."""
    print("🤖 SIMPLE PAPER TRADING BOT WITH DASHBOARD")
    print("=" * 50)
    print("🛡️ SAFE TESTING MODE - NO REAL MONEY AT RISK")
    print()
    print("📋 SETUP REQUIREMENTS:")
    print("1. Install dashboard dependencies:")
    print("   pip install flask")
    print()
    print("2. Start IB Gateway in paper trading mode:")
    print("   - Download IB Gateway from Interactive Brokers")
    print("   - Run in paper trading mode")
    print("   - Enable API connections")
    print("   - Set port: 4002")
    print("   - Add trusted IP: 127.0.0.1")
    print()
    print("3. Run this bot:")
    print("   python simple_paper_bot.py")
    print()
    print("4. Open dashboard:")
    print("   http://127.0.0.1:5000")
    print()
    print("🎯 FEATURES:")
    print("   • Real-time position monitoring")
    print("   • Live P&L tracking")
    print("   • Trade history")
    print("   • Performance metrics")
    print("   • Market status")
    print("=" * 50)

async def main():
    """Main execution with simple dashboard integration."""
    print_simple_paper_trading_info()
    
    # Check if dashboard dependencies are available
    try:
        from dashboard.simple_dashboard import DASHBOARD_AVAILABLE
        if not DASHBOARD_AVAILABLE:
            print("❌ Dashboard dependencies not installed")
            print("Run: pip install flask")
            return
    except ImportError:
        print("❌ Dashboard module not found")
        return
    
    # Create enhanced bot
    bot = SimplePaperTradingBot(CONFIG)
    
    try:
        print("🚀 Starting simple paper trading bot with dashboard...")
        await bot.run_trading_session_with_dashboard()
    except KeyboardInterrupt:
        print("\n⏹️ Simple paper trading bot stopped by user")
        bot.disconnect_from_ib()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        bot.disconnect_from_ib()

if __name__ == "__main__":
    asyncio.run(main())
