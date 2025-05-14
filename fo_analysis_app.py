import streamlit as st
import pandas as pd
import zipfile
import io
from datetime import datetime

st.set_page_config(page_title="F&O Stock Futures Analyzer", layout="wide")
st.title("📈 F&O Stock Futures Analyzer")

# --- Sidebar Inputs ---
st.sidebar.header("🔧 Filter Options")


# Minimum difference input
min_diff = st.sidebar.number_input(
    "Minimum Difference (₹):", min_value=-500.0, max_value=500.0, value=-2.0, step=0.5
)

# Specific stock filter (optional)
selected_stock = st.sidebar.text_input(
    "🔍 View Specific Stock (optional)", help="Enter exact stock name (e.g. INFY, TCS)"
)

# --- Helper Functions ---

# def read_csv_from_zip(zip_bytes):
#     with zipfile.ZipFile(zip_bytes, 'r') as zip_ref:
#         csv_files = [f for f in zip_ref.namelist() if f.endswith('.csv')]
#         for file in csv_files:
#             if file.lower().startswith('fo') and len(file) == 13:  # e.g. fo120525.csv
#                 with zip_ref.open(file) as f:
#                     return pd.read_csv(f)
#     return None

def read_csv_from_zip(zip_bytes):
    with zipfile.ZipFile(zip_bytes, 'r') as zip_ref:
        csv_files = [f for f in zip_ref.namelist() if f.lower().startswith('fo') and f.lower().endswith('.csv')]

        if not csv_files:
            return None

        # Pick the first matching fo*.csv file
        with zip_ref.open(csv_files[0]) as f:
            return pd.read_csv(f)


def parse_expiry(contract):
    try:
        parts = contract.replace("FUTSTK", "")
        stock, expiry = parts[:-11], parts[-11:]  # e.g., ADANIGREEN, 26-JUN-2025
        expiry_date = datetime.strptime(expiry, "%d-%b-%Y")
        return stock.upper(), expiry_date
    except Exception:
        return None, None

def analyze_futures_data(df, min_diff=0.0, selected_stock=None):
    df = df[df['CONTRACT_D'].str.startswith("FUTSTK")]
    df[['Stock', 'Expiry']] = df['CONTRACT_D'].apply(
        lambda x: pd.Series(parse_expiry(x))
    )
    df = df.dropna(subset=['Stock', 'Expiry'])
    df['Expiry'] = pd.to_datetime(df['Expiry'])

    # If specific stock is selected, filter here
    if selected_stock:
        df = df[df['Stock'].str.upper() == selected_stock.upper()]
        if df.empty:
            return pd.DataFrame(), f"No data found for stock: {selected_stock}"

    grouped = df.groupby('Stock')
    result_rows = []
    month_labels = {}

    for stock, group in grouped:
        group = group.sort_values(by='Expiry')
        expiries = group['Expiry'].unique()

        if len(expiries) < 2:
            continue

        expiry_dict = {}
        for i, expiry in enumerate(expiries[:3]):
            label = ['Current', 'Next', 'Far'][i]
            expiry_dict[label] = expiry
            if i < 2:
                month_labels[label] = expiry.strftime('%b')

        prices = {}
        for label, expiry in expiry_dict.items():
            row = group[group['Expiry'] == expiry]
            if not row.empty:
                prices[label] = float(row['CLOSE_PRIC'].mean())
                # prices[label] = float(row.iloc[0]['CLOSE_PRIC'])
                # prices[label] = round(float(row.iloc[0]['CLOSE_PRIC']), 2)


        if 'Current' in prices and 'Next' in prices:
            # price_diff = round(prices['Current'] - prices['Next'], 2)
            
            current_price = prices['Current']
            next_price = prices['Next']
            price_diff = round(next_price - current_price, 2)
            percentage_diff = round((price_diff / current_price) * 100, 2) if current_price != 0 else 0


            if min_diff >= 0:
                # Normal: Next ≥ Current (i.e., Next - Current ≥ min_diff)
                if prices['Next'] - prices['Current'] >= min_diff:
                    result_rows.append({
                        'Stock': stock,
                        f"Next Month ({month_labels['Next']})": prices.get('Next'),
                        f"Current Month ({month_labels['Current']})": prices.get('Current'),
                        "Difference (₹)": price_diff,
                        "Difference (%)": percentage_diff
                        # f"Far Next Month ({month_labels.get('Far', '-')})": prices.get('Far') if 'Far' in prices else None
                    })
            else:
                # Unusual: Next < Current (i.e., Next - Current < min_diff, where min_diff is negative)
                if prices['Next'] - prices['Current'] < min_diff:
                    result_rows.append({
                        'Stock': stock,
                        f"Next Month ({month_labels['Next']})": prices.get('Next'),
                        f"Current Month ({month_labels['Current']})": prices.get('Current'),
                        "Difference (₹)": price_diff,
                        "Difference (%)": percentage_diff
                    })

    return pd.DataFrame(result_rows), None

# --- Main App Interface ---

uploaded_file = st.file_uploader("📤 Upload F&O Bhavcopy (.zip or .csv)", type=['zip', 'csv'])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.zip'):
            df = read_csv_from_zip(uploaded_file)
        elif uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            st.error("Unsupported file format. Upload .zip or .csv only.")
            st.stop()

        if df is not None:
            st.success("✅ File loaded successfully.")
            result_df, stock_msg = analyze_futures_data(df, min_diff=min_diff, selected_stock=selected_stock)

            if stock_msg:
                st.warning(stock_msg)
            elif not result_df.empty:
                behavior_label = "Next ≥ Current" if min_diff >= 0 else "Next < Current"
                st.subheader(f"📊 Stocks where {behavior_label} by ₹{abs(min_diff)} or more")

                st.dataframe(result_df, use_container_width=True)

                # Download CSV
                csv_data = result_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Filtered Data", data=csv_data, file_name="filtered_futures.csv", mime="text/csv")
            else:
                st.info("No matching data found with the given criteria.")
        else:
            st.error("❌ Could not find a valid CSV inside the ZIP file.")
    except Exception as e:
        st.exception(f"Unexpected error: {e}")
