from binance.client import Client
import os

# It's good practice to use environment variables for API keys,
# but for public data endpoints, API key is not strictly needed.
# For this example, we'll assume public endpoints.
# API_KEY = os.environ.get('BINANCE_API_KEY')
# API_SECRET = os.environ.get('BINANCE_API_SECRET')

# client = Client(API_KEY, API_SECRET)
client = Client() # For public data access

def get_klines(symbol, interval, limit=100):
    """
    Fetches kline/candlestick data from Binance.
    :param symbol: Trading symbol (e.g., 'BTCUSDT')
    :param interval: Kline interval (e.g., Client.KLINE_INTERVAL_1HOUR)
    :param limit: Number of klines to fetch (max 1000 for klines)
    :return: List of kline data or None if an error occurs
    """
    try:
        # Fetch klines (candlestick data)
        # Each kline is a list:
        # [
        #   Open time,      (Unix timestamp in milliseconds)
        #   Open,
        #   High,
        #   Low,
        #   Close,          (This is what we usually use for calculations)
        #   Volume,
        #   Close time,
        #   Quote asset volume,
        #   Number of trades,
        #   Taker buy base asset volume,
        #   Taker buy quote asset volume,
        #   Ignore
        # ]
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        return klines
    except Exception as e:
        print(f"Error fetching klines for {symbol}: {e}")
        return None

if __name__ == '__main__':
    # Example usage:
    print("Fetching 1-hour klines for BTCUSDT (last 5):")
    btc_klines = get_klines(symbol='BTCUSDT', interval=Client.KLINE_INTERVAL_1HOUR, limit=5)
    if btc_klines:
        for kline in btc_klines:
            print(f"OpenTime: {kline[0]}, Open: {kline[1]}, High: {kline[2]}, Low: {kline[3]}, Close: {kline[4]}, Volume: {kline[5]}")

    print("\nFetching 1-day klines for ETHUSDT (last 3):")
    eth_klines = get_klines(symbol='ETHUSDT', interval=Client.KLINE_INTERVAL_1DAY, limit=3)
    if eth_klines:
        for kline in eth_klines:
            print(f"Close Price: {kline[4]}")
