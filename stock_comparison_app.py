import streamlit as st
import pandas as pd
import appdirs as ad
ad.user_cache_dir = lambda *args: "/tmp"
import yfinance as yf
import plotly.graph_objects as go
import numpy as np 
import re

COMPANY_SUMMARY_COLS = [
    "shortName",
    "sector",
    "marketCap_billions", 
    "priceToBook",
    "dividendYield"
]

RESIK_FREE_RATE = 0.045  # 10 year us treasury as of May 15, 2024

def calculate_returns_and_volatility(data):
    returns = data.pct_change().dropna()
    annualized_returns = (1 + returns).prod() ** (252 / len(returns)) - 1
    annualized_volatility = returns.std() * np.sqrt(252)
    return annualized_returns, annualized_volatility


# Set page title
st.set_page_config(page_title="Stock Screener")

# List of S&P 500 tickers
tickers = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]["Symbol"].tolist()
tickers = tickers[0:25]
tickers.extend(["^GSPC", "^IXIC"])

# Function to get stock data
@st.cache_data
def get_stock_data(tickers):
    data = yf.download(tickers, period="1y")["Adj Close"]
    return data

# Define filters
market_cap_filter = st.sidebar.slider("Market Cap ($ Billion)", 0.0, 3000.0, (0.0, 3000.0), 0.1)
pb_ratio_filter = st.sidebar.slider("P/B Ratio", 0.0, 100.0, (0.0, 100.0), 0.1)
dividend_yield_filter = st.sidebar.slider("Dividend Yield (%)", 0.0, 10.0, (0.0, 10.0), 0.1)

# Get stock data from Yahoo Finance
stock_data = get_stock_data(tickers)
stock_info = pd.DataFrame([yf.Ticker(ticker).info for ticker in tickers])
stock_info["marketCap_billions"] = stock_info["marketCap"] / 1e9

# Add 'All' category to sector_filter
all_sectors = list(set(stock_info["sector"].tolist()))
sector_filter = st.sidebar.multiselect("Sector", ["All"] + all_sectors, ["All"])

# If 'All' is selected, select all sectors
if "All" in sector_filter:
    sector_filter = all_sectors
else:
    sector_filter = sector_filter

# Filter stocks
filtered_stocks = stock_info[
    (stock_info["marketCap_billions"] >= market_cap_filter[0]) &
    (stock_info["marketCap_billions"] <= market_cap_filter[1]) &
    ((stock_info["priceToBook"].isnull()) |
    (stock_info["priceToBook"] >= pb_ratio_filter[0]) &
    (stock_info["priceToBook"] <= pb_ratio_filter[1])) &
    ((stock_info["dividendYield"].isnull()) |
    (stock_info["dividendYield"] >= dividend_yield_filter[0] / 100) &
    (stock_info["dividendYield"] <= dividend_yield_filter[1] / 100)) &
    (stock_info["sector"].isin(sector_filter))
]
filtered_stocks = filtered_stocks.sort_values('marketCap_billions',
                                               ascending=False)
filtered_stocks = filtered_stocks.set_index("symbol")

# Display filtered stocks
st.subheader(f"Summary of {len(filtered_stocks)} Filtered Stocks")
st.dataframe(filtered_stocks[COMPANY_SUMMARY_COLS])

# Display stock charts
# st.subheader("Stock Charts")
# stock_symbols = filtered_stocks.index.tolist()
# default_tickers = ["^GSPC", "^IXIC"]
# selected_tickers = st.multiselect("Select Stocks", 
#                                   stock_symbols +default_tickers,
#                                   default_tickers)

# if selected_tickers:
#     charts = st.columns(len(selected_tickers))
#     for i, ticker in enumerate(selected_tickers):
#         with charts[i]:
#             if ticker == "^GSPC":
#                 st.subheader("S&P 500")
#             elif ticker == "^IXIC":
#                 st.subheader("Nasdaq Composite")
#             else:
#                 st.subheader(ticker)
#             st.line_chart(stock_data[ticker])

# Display stock charts
st.subheader("Select Stocks for comparison")
default_tickers = ["S&P 500 Index", "Nasdaq Composite Index"]
selected_tickers = st.multiselect("Select Stocks2", filtered_stocks.index.tolist() + default_tickers, default_tickers)


st.subheader("Metrics:")
metrics = pd.DataFrame(index=selected_tickers) # Metrics dataframe
for ticker in selected_tickers:
    ticker_symbol = "^GSPC" if ticker == "S&P 500 Index" else "^IXIC" if ticker == "Nasdaq Composite Index" else ticker
    returns = stock_data[ticker_symbol].pct_change().dropna()
    annualized_returns, annualized_volatility = calculate_returns_and_volatility(stock_data[ticker_symbol])
    sharpe_ratio = (annualized_returns - RESIK_FREE_RATE) / annualized_volatility
    metrics.loc[ticker, "Annualized Returns"] = annualized_returns
    metrics.loc[ticker, "Annualized Volatility"] = annualized_volatility
    metrics.loc[ticker, "Sharpe Ratio"] = sharpe_ratio

# Display metrics table
st.subheader("Stock Metrics")
st.dataframe(metrics)

st.subheader("Plots:")
if selected_tickers:
    # Create a line chart with Plotly
    fig = go.Figure()

    for ticker in selected_tickers:
        if ticker in stock_data.columns or ticker in ["S&P 500 Index", "Nasdaq Composite Index"]:
            ticker_symbol = "^GSPC" if ticker == "S&P 500 Index" else "^IXIC" if ticker == "Nasdaq Composite Index" else ticker

            cumulative_change = (stock_data[ticker_symbol] / stock_data[ticker_symbol].iloc[0]) - 1
            fig.add_trace(go.Scatter(x=cumulative_change.index, y=cumulative_change, mode='lines', name=ticker))

    fig.update_layout(
        title="Stock Cumulative Change",
        xaxis_title="Date",
        yaxis_title="Cumulative Change",
        legend_title="Tickers",
        xaxis_rangeslider_visible=False,
        xaxis_tickformat="%b-%y" 
    )

    st.plotly_chart(fig, use_container_width=True)
