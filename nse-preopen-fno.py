import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz

st.set_page_config(page_title="F&O Pre-Open Market Filter", layout="wide")
st.title("F&O Pre-Open Market Filter")


# Function to fetch 15-min high/low using yfinance
def get_first_15min_high_low(symbol):
    try:
        symbol_yahoo = f"{symbol}.NS"
        df_intraday = yf.download(
            tickers=symbol_yahoo, period="1d", interval="1m", progress=False
        )

        if df_intraday.empty:
            return None, None

        # Convert index to IST
        df_intraday.index = df_intraday.index.tz_localize("UTC").tz_convert(
            "Asia/Kolkata"
        )
        first_15 = df_intraday.between_time("09:15", "09:30")
        high = first_15["High"].max()
        low = first_15["Low"].min()
        return high, low

    except Exception as e:
        return None, None


uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # Clean columns
    df.columns = df.columns.str.strip()
    df.rename(
        columns={
            "CHNG": "CHANGE",
            "%CHNG": "PCT_CHANGE",
            "PREV. CLOSE": "PREV_CLOSE",
            "FINAL": "P.O. Price",
        },
        inplace=True,
    )

    df["PCT_CHANGE"] = pd.to_numeric(df["PCT_CHANGE"], errors="coerce")
    df["CHANGE"] = pd.to_numeric(df["CHANGE"], errors="coerce")
    df["PREV_CLOSE"] = df["PREV_CLOSE"].astype(str).str.replace(",", "")
    df["PREV_CLOSE"] = pd.to_numeric(df["PREV_CLOSE"], errors="coerce")

    # Sidebar filters
    st.sidebar.header("Filter Settings")
    lower_positive = st.sidebar.number_input("Lower Positive %", value=2.0)
    upper_positive = st.sidebar.number_input("Upper Positive %", value=3.0)
    lower_negative = st.sidebar.number_input("Lower Negative %", value=-3.0)
    upper_negative = st.sidebar.number_input("Upper Negative %", value=-2.0)
    min_prev_close = st.sidebar.number_input("Minimum Prev. Close", value=100.0)

    # Apply filters
    filtered_df = df[
        (
            (
                (df["PCT_CHANGE"] >= lower_positive)
                & (df["PCT_CHANGE"] <= upper_positive)
            )
            | (
                (df["PCT_CHANGE"] >= lower_negative)
                & (df["PCT_CHANGE"] <= upper_negative)
            )
        )
        & (df["PREV_CLOSE"] >= min_prev_close)
    ]

    filtered_df = filtered_df.sort_values(by="PCT_CHANGE", ascending=False)

    # Fetch intraday high/low for each symbol
    # st.write("### Fetching first 15-min High/Low (from Yahoo Finance)...")
    # highs = []
    # lows = []
    # for sym in filtered_df["SYMBOL"]:
    #     # high, low = get_first_15min_high_low(sym)
    #     high = 0
    #     low = 0
    #     highs.append(high)
    #     lows.append(low)

    filtered_df["15min High"] = 0
    filtered_df["15min Low"] = 0

    # Display result
    st.write("### Filtered Stocks")
    display_columns = [
        "SYMBOL",
        "PREV_CLOSE",
        "CHANGE",
        "PCT_CHANGE",
        "P.O. Price",
        "15min High",
        "15min Low",
    ]
    st.dataframe(filtered_df[display_columns].reset_index(drop=True))
