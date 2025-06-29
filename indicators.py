import pandas as pd
import numpy as np

def calculate_sma(prices, window):
    """
    Calculates the Simple Moving Average (SMA).
    :param prices: List or Pandas Series of prices (typically close prices).
    :param window: The period for the SMA.
    :return: Pandas Series containing the SMA values.
    """
    if len(prices) < window:
        return pd.Series([np.nan] * len(prices)) # Not enough data
    return pd.Series(prices).rolling(window=window).mean()

def calculate_ema(prices, window):
    """
    Calculates the Exponential Moving Average (EMA).
    :param prices: List or Pandas Series of prices.
    :param window: The period for the EMA.
    :return: Pandas Series containing the EMA values.
    """
    if len(prices) < window: # EMA needs at least 'window' points to start reasonably
        return pd.Series([np.nan] * len(prices))
    return pd.Series(prices).ewm(span=window, adjust=False).mean()

def calculate_rsi(prices, window=14):
    """
    Calculates the Relative Strength Index (RSI).
    :param prices: List or Pandas Series of prices (typically close prices).
    :param window: The period for the RSI (commonly 14).
    :return: Pandas Series containing the RSI values.
    """
    if len(prices) < window + 1: # Need at least window + 1 prices for one RSI value
        return pd.Series([np.nan] * len(prices))

    delta = pd.Series(prices).diff(1)
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=window, min_periods=1).mean()
    avg_loss = loss.rolling(window=window, min_periods=1).mean()

    # Smoothed RSI (using Wilder's smoothing)
    # Initialize first avg_gain and avg_loss
    # For subsequent periods: AvgGain = ((previous AvgGain) * (n-1) + current Gain) / n
    # This is more complex. For simplicity, using rolling mean for first pass.
    # A more accurate Wilder's smoothing for RSI:
    # avg_gain = gain.ewm(alpha=1/window, adjust=False).mean()
    # avg_loss = loss.ewm(alpha=1/window, adjust=False).mean()

    # Simplified RSI using rolling mean for average gain/loss
    # This is not the standard RSI calculation but often used as a proxy if TA-Lib isn't available.
    # For a more standard RSI, TA-Lib is recommended or a more detailed Wilder's smoothing implementation.
    # Let's use a common pandas approach for RSI:

    delta = pd.Series(prices).diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    # Ensure RSI is within 0-100, handle division by zero if loss is 0
    rsi = rsi.replace([np.inf, -np.inf], 100) # If loss is 0, RS is inf, RSI is 100
    rsi = rsi.fillna(50) # Or some other neutral value for initial NaNs

    return rsi


def calculate_macd(prices, short_window=12, long_window=26, signal_window=9):
    """
    Calculates the Moving Average Convergence Divergence (MACD).
    :param prices: List or Pandas Series of prices.
    :param short_window: Period for the short-term EMA.
    :param long_window: Period for the long-term EMA.
    :param signal_window: Period for the signal line EMA.
    :return: Tuple of Pandas Series (MACD line, Signal line, Histogram).
    """
    if len(prices) < long_window: # Need enough data for the longest EMA
        nan_series = pd.Series([np.nan] * len(prices))
        return nan_series, nan_series, nan_series

    ema_short = calculate_ema(prices, short_window)
    ema_long = calculate_ema(prices, long_window)

    macd_line = ema_short - ema_long
    signal_line = calculate_ema(macd_line, signal_window)
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram

if __name__ == '__main__':
    # Example Usage:
    # Dummy prices for testing
    dummy_prices = [
        10, 11, 12, 13, 12, 11, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
        19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 7, 8, 9, 10
    ]
    price_series = pd.Series(dummy_prices)

    print("Calculating SMA (window 5):")
    sma5 = calculate_sma(price_series, 5)
    print(sma5.tail())

    print("\nCalculating EMA (window 5):")
    ema5 = calculate_ema(price_series, 5)
    print(ema5.tail())

    print("\nCalculating RSI (window 14):")
    # Need more data for a good RSI example, but let's try
    rsi14 = calculate_rsi(price_series, 14)
    print(rsi14.tail())

    print("\nCalculating MACD (12, 26, 9):")
    macd_line, signal_line, hist = calculate_macd(price_series)
    print("MACD Line:\n", macd_line.tail())
    print("Signal Line:\n", signal_line.tail())
    print("Histogram:\n", hist.tail())

    # Test with fewer prices to check NaN handling
    short_prices = [10,11,12,13,14]
    print("\nCalculating SMA (window 10) with insufficient data:")
    sma10_short = calculate_sma(pd.Series(short_prices), 10)
    print(sma10_short)

    print("\nCalculating RSI (window 14) with insufficient data:")
    rsi14_short = calculate_rsi(pd.Series(short_prices), 14)
    print(rsi14_short)

    print("\nCalculating MACD (12,26,9) with insufficient data:")
    m, s, h = calculate_macd(pd.Series(short_prices))
    print(m)
