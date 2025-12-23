"""
AI Day Trader - Main Entry Point
Orchestrates all components and provides CLI interface
"""
import asyncio
import sys
import signal
from pathlib import Path
from typing import Optional
from decimal import Decimal
import argparse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich import print as rprint

from config.settings import get_settings, Settings
from src.broker import AlpacaBroker, PaperTradingBroker
from src.data import MarketDataProvider
from src.analysis import TechnicalAnalyzer, PatternRecognizer, SignalGenerator
from src.ai import DecisionEngine, LLMAnalyzer, TradingAgent
from src.trading import RiskManager, TradeExecutor, PortfolioManager


console = Console()


def setup_logging(log_level: str = "INFO"):
    """Configure logging."""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
        level=log_level,
        colorize=True
    )

    # File logging
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    logger.add(
        log_dir / "trading_{time}.log",
        rotation="1 day",
        retention="7 days",
        level="DEBUG"
    )


async def create_components(settings: Settings, paper_mode: bool = True):
    """Create and initialize all trading components."""

    # Create broker
    if paper_mode:
        broker = PaperTradingBroker(initial_cash=Decimal("10000"))
    else:
        broker = AlpacaBroker(
            api_key=settings.api_keys.alpaca_api_key,
            secret_key=settings.api_keys.alpaca_secret_key,
            paper_trading=settings.trading.mode == "paper"
        )

    # Connect broker
    connected = await broker.connect()
    if not connected:
        raise ConnectionError("Failed to connect to broker")

    # Create data provider
    data_provider = MarketDataProvider(
        alpaca_api_key=settings.api_keys.alpaca_api_key,
        alpaca_secret_key=settings.api_keys.alpaca_secret_key
    )

    # Create analysis components
    ta = TechnicalAnalyzer()
    pr = PatternRecognizer()
    sg = SignalGenerator(ta, pr)

    # Create LLM analyzer (optional)
    llm = None
    if settings.api_keys.anthropic_api_key:
        try:
            llm = LLMAnalyzer(
                api_key=settings.api_keys.anthropic_api_key,
                provider="anthropic",
                model=settings.ai.llm_model,
                temperature=settings.ai.llm_temperature
            )
        except Exception as e:
            logger.warning(f"Failed to initialize LLM: {e}")

    # Create decision engine
    decision_engine = DecisionEngine(
        technical_analyzer=ta,
        pattern_recognizer=pr,
        signal_generator=sg,
        llm_analyzer=llm,
        min_confidence=settings.ai.min_confidence_to_trade,
        use_llm=settings.ai.use_llm_reasoning and llm is not None
    )

    # Create risk manager
    risk_manager = RiskManager(config=settings.trading)

    # Create executor
    executor = TradeExecutor(broker, risk_manager)

    # Create portfolio manager
    portfolio = PortfolioManager(broker)

    # Create trading agent
    agent = TradingAgent(
        broker=broker,
        data_provider=data_provider,
        decision_engine=decision_engine,
        settings=settings,
        symbols=settings.trading.symbols,
        timeframe=settings.trading.default_timeframe
    )

    return {
        "broker": broker,
        "data_provider": data_provider,
        "decision_engine": decision_engine,
        "risk_manager": risk_manager,
        "executor": executor,
        "portfolio": portfolio,
        "agent": agent
    }


async def run_trading_bot(settings: Settings, paper_mode: bool = True):
    """Run the trading bot."""
    console.print(Panel.fit(
        "[bold cyan]🤖 AI Day Trader[/bold cyan]\n"
        "[dim]Autonomous Trading System[/dim]",
        border_style="cyan"
    ))

    mode_text = "[yellow]PAPER TRADING[/yellow]" if paper_mode else "[red]LIVE TRADING[/red]"
    console.print(f"\nMode: {mode_text}")
    console.print(f"Symbols: {', '.join(settings.trading.symbols)}")
    console.print(f"Timeframe: {settings.trading.default_timeframe}")
    console.print()

    # Create components
    components = await create_components(settings, paper_mode)
    agent = components["agent"]
    portfolio = components["portfolio"]

    # Setup shutdown handler
    shutdown_event = asyncio.Event()

    def handle_shutdown(signum, frame):
        console.print("\n[yellow]Shutting down...[/yellow]")
        shutdown_event.set()

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    # Start the agent
    await agent.start()

    console.print("[green]✓ Agent started successfully![/green]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    # Display live status
    try:
        while not shutdown_event.is_set():
            # Get status
            status = await agent.get_status()
            state = await portfolio.get_state()

            # Print status
            table = Table(title="Trading Status", show_header=True)
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Agent State", status["state"])
            table.add_row("Portfolio Value", f"${float(state.equity):,.2f}")
            table.add_row("Cash", f"${float(state.cash):,.2f}")
            table.add_row("Unrealized P&L", f"${float(state.unrealized_pnl):,.2f}")
            table.add_row("Open Positions", str(len(state.positions)))
            table.add_row("Total Decisions", str(status["stats"]["total_decisions"]))
            table.add_row("Trades Executed", str(status["stats"]["trades_executed"]))

            console.print(table)

            await asyncio.sleep(30)  # Update every 30 seconds

    except asyncio.CancelledError:
        pass
    finally:
        await agent.stop()
        console.print("[green]Agent stopped.[/green]")


async def run_backtest(settings: Settings, days: int = 30):
    """Run a backtest on historical data."""
    console.print(Panel.fit(
        "[bold cyan]📊 Backtest Mode[/bold cyan]\n"
        f"[dim]Testing strategy on {days} days of data[/dim]",
        border_style="cyan"
    ))

    # Create components
    components = await create_components(settings, paper_mode=True)
    decision_engine = components["decision_engine"]
    data_provider = components["data_provider"]

    # TODO: Implement full backtesting engine
    console.print("[yellow]Backtest engine coming soon![/yellow]")


def run_dashboard():
    """Run the Streamlit dashboard."""
    import subprocess
    dashboard_path = Path(__file__).parent / "ui" / "dashboard.py"
    subprocess.run(["streamlit", "run", str(dashboard_path)])


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AI Day Trader - Autonomous Trading System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main trade --paper          Start paper trading
  python -m src.main trade --live           Start live trading (CAREFUL!)
  python -m src.main dashboard              Launch the web dashboard
  python -m src.main backtest --days 30     Run backtest
  python -m src.main status                 Show current status
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Trade command
    trade_parser = subparsers.add_parser("trade", help="Start trading")
    trade_parser.add_argument("--paper", action="store_true", default=True, help="Paper trading mode")
    trade_parser.add_argument("--live", action="store_true", help="Live trading mode")
    trade_parser.add_argument("--symbols", nargs="+", help="Symbols to trade")
    trade_parser.add_argument("--timeframe", default="1h", help="Trading timeframe")

    # Dashboard command
    dash_parser = subparsers.add_parser("dashboard", help="Launch web dashboard")
    dash_parser.add_argument("--port", type=int, default=8501, help="Dashboard port")

    # Backtest command
    backtest_parser = subparsers.add_parser("backtest", help="Run backtest")
    backtest_parser.add_argument("--days", type=int, default=30, help="Days of data")
    backtest_parser.add_argument("--symbols", nargs="+", help="Symbols to test")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show status")

    # Parse arguments
    args = parser.parse_args()

    # Setup logging
    setup_logging()

    # Get settings
    settings = get_settings()

    # Execute command
    if args.command == "trade":
        paper_mode = not args.live
        if args.symbols:
            settings.trading.symbols = args.symbols
        if args.timeframe:
            settings.trading.default_timeframe = args.timeframe

        if not paper_mode:
            console.print("[bold red]⚠️  WARNING: LIVE TRADING MODE[/bold red]")
            console.print("[red]This will use REAL money! Are you sure? (yes/no)[/red]")
            confirm = input()
            if confirm.lower() != "yes":
                console.print("Aborted.")
                return

        asyncio.run(run_trading_bot(settings, paper_mode))

    elif args.command == "dashboard":
        run_dashboard()

    elif args.command == "backtest":
        asyncio.run(run_backtest(settings, args.days))

    elif args.command == "status":
        console.print("[cyan]Status check coming soon![/cyan]")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
