"""
Example: Running a backtest
"""

from datetime import datetime, timedelta
from src.data.data_fetcher import DataFetcher
from src.backtest.backtest_engine import BacktestEngine
from config import Config

def main():
    # Initialize components
    data_fetcher = DataFetcher()
    backtest_engine = BacktestEngine(initial_capital=100000)
    
    # Define parameters
    symbol = "RELIANCE"
    start_date = datetime(2004, 1, 1)
    end_date = datetime.now()
    
    print(f"Fetching historical data for {symbol}...")
    
    # Fetch data
    df = data_fetcher.fetch_historical_data(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        source='yahoo'
    )
    
    if df.empty:
        print("No data available")
        return
    
    # Prepare data
    df = data_fetcher.prepare_data_for_backtest(df)
    print(f"Data prepared: {len(df)} records")
    
    # Run backtest
    print("Running backtest...")
    results = backtest_engine.run_backtest(df, symbol)
    
    # Print results
    print("\n" + "="*60)
    print("BACKTEST RESULTS")
    print("="*60)
    print(f"Total Trades: {results['total_trades']}")
    print(f"Win Rate: {results['win_rate']:.2f}%")
    print(f"CAGR: {results['cagr']:.2f}%")
    print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {results['max_drawdown']:.2f}%")
    print(f"Total Return: {results['total_return']:.2f}%")
    print(f"Final Capital: ₹{results['final_capital']:,.2f}")
    
    # Generate report and plots
    backtest_engine.generate_report(results, symbol, Config.BACKTEST_RESULTS_PATH)
    backtest_engine.plot_results(results, symbol, Config.BACKTEST_RESULTS_PATH)
    
    print(f"\nReport and charts saved to {Config.BACKTEST_RESULTS_PATH}")

if __name__ == "__main__":
    main()
