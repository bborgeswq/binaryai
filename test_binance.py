"""
Test Binance Testnet Connection
"""
import asyncio
from src.broker.binance_client import BinanceBroker

# Testnet API Keys
API_KEY = "028sJM50z6LApmam3rRbV7xrdbVvcXsNV2PKBBGtyXbzIvfe7oXOUrk1TXXFy83f"
SECRET_KEY = "3FWoIwQGXfOh23t1p5XIIYRIt6waPNZnUT4esZdBZBodk6vkRTD0RbX9RxkOmhWb"


async def test_connection():
    print("=" * 50)
    print("Testing Binance Testnet Connection")
    print("=" * 50)

    # Create broker
    broker = BinanceBroker(
        api_key=API_KEY,
        secret_key=SECRET_KEY,
        testnet=True
    )

    # Connect
    print("\n1. Connecting to Binance Testnet...")
    connected = await broker.connect()

    if not connected:
        print("❌ Failed to connect!")
        return

    print("✅ Connected successfully!")

    # Get account
    print("\n2. Getting account info...")
    account = await broker.get_account()
    print(f"   Account ID: {account.account_id}")
    print(f"   Equity: {account.equity} USDT")
    print(f"   Cash: {account.cash} USDT")

    # Get BTC price
    print("\n3. Getting BTC/USDT price...")
    ticker = await broker.get_ticker("BTC/USDT")
    print(f"   BTC Price: ${ticker.get('last', 'N/A')}")
    print(f"   24h High: ${ticker.get('high', 'N/A')}")
    print(f"   24h Low: ${ticker.get('low', 'N/A')}")

    # Get ETH price
    print("\n4. Getting ETH/USDT price...")
    ticker_eth = await broker.get_ticker("ETH/USDT")
    print(f"   ETH Price: ${ticker_eth.get('last', 'N/A')}")

    # Get positions
    print("\n5. Getting positions...")
    positions = await broker.get_positions()
    if positions:
        for p in positions:
            print(f"   {p.symbol}: {p.quantity} @ ${p.current_price}")
    else:
        print("   No open positions")

    # Get OHLCV data
    print("\n6. Getting recent candles (BTC/USDT 1h)...")
    ohlcv = await broker.get_ohlcv("BTC/USDT", "1h", 5)
    if ohlcv:
        print(f"   Last 5 candles loaded")
        last_candle = ohlcv[-1]
        print(f"   Latest: O:{last_candle[1]} H:{last_candle[2]} L:{last_candle[3]} C:{last_candle[4]}")

    print("\n" + "=" * 50)
    print("✅ All tests passed! Binance Testnet is working!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(test_connection())
