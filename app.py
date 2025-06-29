from flask import Flask, jsonify, render_template # Added render_template
from apscheduler.schedulers.background import BackgroundScheduler
import time
import pandas as pd

from binance_client import get_klines, Client # Import Client for KLINE_INTERVAL constants
from indicators import calculate_sma, calculate_rsi, calculate_macd
from trading_logic import generate_signals
from scheduler import start_scheduler

app = Flask(__name__) # Flask will look for templates in a 'templates' folder

# In-memory store for the latest advice
latest_advice = {
    "BTCUSDT": {"signal": "N/A", "details": "Not yet analyzed", "indicators": {}},
    "ETHUSDT": {"signal": "N/A", "details": "Not yet analyzed", "indicators": {}},
    "XRPUSDT": {"signal": "N/A", "details": "Not yet analyzed", "indicators": {}},
    "SOLUSDT": {"signal": "N/A", "details": "Not yet analyzed", "indicators": {}},
}

SYMBOLS_TO_ANALYZE = ["BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT"]
KLINE_INTERVAL = Client.KLINE_INTERVAL_1HOUR # Fetch 1-hour candles
KLINE_LIMIT = 100 # Fetch last 100 candles for indicator calculation (RSI needs n+1, MACD needs long_window)

def analyze_symbol(symbol):
    """
    Performs analysis for a single symbol.
    Fetches data, calculates indicators, and generates a signal.
    """
    print(f"Analyzing {symbol}...")
    # Ensure enough data for all indicators, e.g., MACD long window (26) + signal window (9) for EMA smoothing,
    # and RSI window (14) + 1. Pandas rolling/ewm might handle fewer points by returning NaNs.
    # KLINE_LIMIT should be sufficient (e.g., 100 points for up to ~35 periods of MACD/RSI).
    klines = get_klines(symbol=symbol, interval=KLINE_INTERVAL, limit=KLINE_LIMIT)

    if not klines or len(klines) < 30: # Minimum check, some indicators might need more for stability
        print(f"Could not fetch sufficient kline data for {symbol} (need at least 30 points). Got {len(klines) if klines else 0}")
        return {"signal": "ERROR", "details": f"Insufficient data ({len(klines) if klines else 0} points)", "indicators": {}}

    close_prices = [float(kline[4]) for kline in klines]
    price_series = pd.Series(close_prices)

    # Calculate indicators
    # .iloc[-1] gets the last value of the series
    sma20_series = calculate_sma(price_series, 20)
    sma20 = sma20_series.iloc[-1] if not sma20_series.empty else float('nan')

    rsi14_series = calculate_rsi(price_series, 14)
    rsi14 = rsi14_series.iloc[-1] if not rsi14_series.empty else float('nan')

    macd_line_series, macd_signal_series, _ = calculate_macd(price_series, 12, 26, 9)
    macd_line = macd_line_series.iloc[-1] if not macd_line_series.empty else float('nan')
    macd_signal = macd_signal_series.iloc[-1] if not macd_signal_series.empty else float('nan')

    current_indicators = {
        "rsi": rsi14 if pd.notna(rsi14) else None,
        "macd_line": macd_line if pd.notna(macd_line) else None,
        "macd_signal": macd_signal if pd.notna(macd_signal) else None,
        "sma20": sma20 if pd.notna(sma20) else None,
        "current_price": price_series.iloc[-1] if not price_series.empty else None
    }

    signal = generate_signals(current_indicators)

    print(f"Analysis for {symbol}: Signal={signal}, Indicators={current_indicators}")
    return {
        "signal": signal,
        "details": f"Analyzed at {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "indicators": current_indicators
    }

def perform_global_analysis():
    """
    This function will be called hourly to perform the market analysis
    for all configured symbols.
    """
    print(f"Performing global analysis at {time.strftime('%Y-%m-%d %H:%M:%S')}...")
    global latest_advice
    for symbol in SYMBOLS_TO_ANALYZE:
        try:
            advice_data = analyze_symbol(symbol)
            latest_advice[symbol] = advice_data
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            latest_advice[symbol] = {"signal": "ERROR", "details": str(e), "indicators": {}}

    print(f"Global analysis complete. Latest advice: {latest_advice}")

@app.route('/api/advice', methods=['GET'])
def get_advice_api(): # Renamed to avoid conflict with any 'get_advice' variable
    """
    API endpoint to get the latest trading advice.
    """
    return jsonify(latest_advice)

@app.route('/', methods=['GET'])
def home():
    """
    Serves the main HTML page.
    """
    return render_template('index.html')

if __name__ == '__main__':
    perform_global_analysis()
    analysis_scheduler = start_scheduler(job_function=perform_global_analysis, interval_hours=1)
    print("Flask app starting...")
    app.run(debug=True, use_reloader=False)
    # Proper scheduler shutdown (won't be reached in typical debug run)
    # if analysis_scheduler:
    #     analysis_scheduler.shutdown()
    # print("Scheduler shut down.")
