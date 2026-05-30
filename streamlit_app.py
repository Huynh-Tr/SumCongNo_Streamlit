import streamlit as st
import pandas as pd
from io import BytesIO, StringIO
import numpy as np
import re

# Configure the page
st.set_page_config(
    page_title="Excel Summary",
    page_icon="📊",
    layout="centered",  # Better for mobile
    initial_sidebar_state="collapsed"
)

# Title - Simple and clean
st.title("📊 Excel Summary")
st.caption("Upload • Paste • Analyze")

# iPhone-optimized CSS
st.markdown("""
<style>
    /* iPhone optimization */
    .main .block-container {
        padding: 1rem 0.75rem;
        max-width: 100%;
    }
    
    /* Beautiful typography for iPhone */
    h1 {
        font-size: 1.75rem !important;
        font-weight: 700 !important;
        margin-bottom: 0.25rem !important;
        letter-spacing: -0.02em;
    }
    
    .stCaption {
        font-size: 0.875rem !important;
        color: #6B7280 !important;
        margin-bottom: 1.5rem !important;
    }
    
    /* Clean buttons */
    .stButton button {
        width: 100%;
        padding: 0.875rem;
        font-size: 1rem;
        font-weight: 600;
        border-radius: 0.75rem;
        border: none;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
    }
    
    /* File uploader */
    .stFileUploader {
        font-size: 0.9rem;
    }
    
    .stFileUploader > div > button {
        border-radius: 0.75rem;
        font-size: 0.9rem;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 0.75rem 1.25rem;
        font-size: 0.95rem;
        font-weight: 600;
        border-radius: 0.75rem;
    }
    
    /* Multiselect */
    .stMultiSelect {
        font-size: 0.9rem;
    }
    
    /* Selectbox */
    .stSelectbox {
        font-size: 0.9rem;
    }
    
    /* Metrics */
    [data-testid="stMetric"] {
        background-color: #F9FAFB;
        padding: 1rem;
        border-radius: 0.75rem;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.8rem;
        font-weight: 600;
        color: #6B7280;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 1.5rem;
        font-weight: 700;
        color: #111827;
    }
    
    /* Dataframe */
    .stDataFrame {
        font-size: 0.85rem;
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Initialize session state for processed DataFrame
if "df_processed" not in st.session_state:
    st.session_state.df_processed = None

def clean_empty_rows_and_columns(df):
    """
    Remove completely empty rows and columns, and rows/columns with mostly null values.
    Returns: cleaned DataFrame
    """
    if df is None or df.empty:
        return df

    # Calculate null threshold (80% or more nulls = remove)
    null_threshold = 0.8

    # Remove rows with too many nulls
    row_null_ratio = df.isna().mean(axis=1)
    df = df.loc[row_null_ratio < null_threshold].reset_index(drop=True)
    if df.empty:
        return df

    # Remove completely empty columns (after row filtering)
    df = df.loc[:, df.notna().any()]
    if df.empty:
        return df

    # Remove leading/trailing sparse rows (faster than python loops)
    non_null_counts = df.notna().sum(axis=1).to_numpy()
    keep_mask = non_null_counts >= 3
    if keep_mask.any():
        first = int(np.argmax(keep_mask))
        last = int(len(keep_mask) - 1 - np.argmax(keep_mask[::-1]))
        df = df.iloc[first:last + 1].reset_index(drop=True)

    # Remove completely empty columns again after trimming
    df = df.loc[:, df.notna().any()]
    return df

def simplify_dataframe(df):
    """
    Simplify DataFrame by:
    1. Naming columns as Col_0, Col_1, etc.
    Returns: simplified DataFrame
    """
    # Rename columns to simple numeric names
    df.columns = [f'Col_{i}' for i in range(len(df.columns))]
    
    return df

def convert_numeric_columns(df):
    """
    Try to convert object columns to numeric where it makes sense.
    This helps expose more columns in the numeric 'sum' selections.
    """
    for col in df.columns:
        if df[col].dtype == object:
            non_null_count = int(df[col].notna().sum())
            if non_null_count == 0:
                continue

            sample = df[col].dropna().astype(str).head(30)
            if not sample.str.contains(r"\d", regex=True).any():
                continue

            # Attempt numeric conversion
            raw = df[col].astype(str).str.replace(',', '', regex=False)
            converted = pd.to_numeric(raw, errors='coerce')
            # If at least 50% of non-null values become numeric, keep conversion
            converted_count = int(converted.notna().sum())
            if converted_count >= 0.5 * non_null_count and converted_count > 0:
                df[col] = converted
    return df

_THOUSANDS_COMMA_RE = re.compile(r"^[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?$")
_THOUSANDS_DOT_RE = re.compile(r"^[+-]?\d{1,3}(?:\.\d{3})+(?:,\d+)?$")
_ONLY_THOUSANDS_COMMA_RE = re.compile(r"^[+-]?\d{1,3}(?:,\d{3})+$")
_ONLY_THOUSANDS_DOT_RE = re.compile(r"^[+-]?\d{1,3}(?:\.\d{3})+$")
_DECIMAL_COMMA_RE = re.compile(r"^[+-]?\d+(?:,\d+)$")

def _normalize_number_token(token: str) -> str:
    """
    Normalize a single token that may represent a number.
    Examples:
      - "2,105,000" -> "2105000"
      - "1.234,56"  -> "1234.56"
      - "1,234.56"  -> "1234.56"
    """
    t = token.strip()
    if not t:
        return token
    if "," not in t and "." not in t:
        return t

    # Fast-path common thousand separators
    if _THOUSANDS_COMMA_RE.match(t) or _ONLY_THOUSANDS_COMMA_RE.match(t):
        return t.replace(",", "")
    if _THOUSANDS_DOT_RE.match(t) or _ONLY_THOUSANDS_DOT_RE.match(t):
        return t.replace(".", "").replace(",", ".")

    # Mixed separators: pick the last seen separator as decimal mark.
    if "," in t and "." in t:
        if t.rfind(",") > t.rfind("."):
            # "1.234,56" -> "1234.56"
            return t.replace(".", "").replace(",", ".")
        # "1,234.56" -> "1234.56"
        return t.replace(",", "")

    # Only comma: could be decimal or thousands
    if "," in t:
        if _ONLY_THOUSANDS_COMMA_RE.match(t):
            return t.replace(",", "")
        if _DECIMAL_COMMA_RE.match(t):
            return t.replace(",", ".")
        return t

    # Only dot: could be thousands
    if "." in t and _ONLY_THOUSANDS_DOT_RE.match(t):
        return t.replace(".", "")

    return t

def _format_metric_number(value) -> str:
    if value is None:
        return ""
    try:
        v = float(value)
    except Exception:
        return str(value)
    if not np.isfinite(v):
        return str(value)
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    s = f"{v:.6f}".rstrip("0").rstrip(".")
    return s

def _format_metric_number_grouped(value) -> str:
    if value is None:
        return ""
    try:
        v = float(value)
    except Exception:
        return str(value)
    if not np.isfinite(v):
        return str(value)
    if abs(v - round(v)) < 1e-9:
        return f"{int(round(v)):,}"
    s = f"{v:,.6f}".rstrip("0").rstrip(".")
    return s

def _format_table_number_grouped(value) -> str:
    if value is None:
        return ""
    try:
        v = float(value)
    except Exception:
        return str(value)
    if not np.isfinite(v):
        return str(value)
    if abs(v - round(v)) < 1e-9:
        return f"{int(round(v)):,}"
    return f"{v:,.2f}"

def parse_pasted_data(text):
    """
    Parse pasted text data into DataFrame.
    Supports: tab-separated, comma-separated, or space-separated.
    Pre-processes numbers: handles thousand separators like "2,105,000" -> "2105000"
    Returns: DataFrame or None if parsing fails
    """
    if not text or not text.strip():
        return None
    
    try:
        # Pre-process text to normalize numbers without breaking delimiters.
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # For each line, process potential numeric values
            # - If tab-separated (Excel copy), keep tabs.
            # - If comma exists, it can be a delimiter or a thousand separator.
            if '\t' in line:
                parts = line.split('\t')
                joiner = '\t'
            elif ',' in line:
                # Single numeric value like "2,105,000" should stay as one token.
                candidate = line.strip()
                if _THOUSANDS_COMMA_RE.match(candidate) or _ONLY_THOUSANDS_COMMA_RE.match(candidate):
                    parts = [candidate]
                    joiner = ' '
                else:
                    parts = line.split(',')
                    # We'll re-join with tab to avoid confusing commas later.
                    joiner = '\t'
            else:
                parts = line.split()
                joiner = ' '
            cleaned_parts = []
            for part in parts:
                cleaned_parts.append(_normalize_number_token(part))

            cleaned_lines.append(joiner.join(cleaned_parts))
        
        cleaned_text = '\n'.join(cleaned_lines)
        
        # Try tab-separated first (most common from Excel copy)
        if '\t' in cleaned_text:
            df = pd.read_csv(StringIO(cleaned_text), sep='\t', header=None)
        # Try comma-separated
        elif ',' in cleaned_text:
            df = pd.read_csv(StringIO(cleaned_text), sep=',', header=None)
        # Try space/whitespace separated
        else:
            df = pd.read_csv(StringIO(cleaned_text), sep=r'\s+', header=None, engine='python')
        
        return df if not df.empty else None
    except Exception:
        return None

def _process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = clean_empty_rows_and_columns(df)
    if df is None or df.empty:
        return df
    df = simplify_dataframe(df)
    df = convert_numeric_columns(df)
    return df

@st.cache_data(show_spinner=False, ttl=3600, max_entries=20)
def _process_uploaded_excel_bytes(file_bytes: bytes) -> pd.DataFrame:
    df = pd.read_excel(BytesIO(file_bytes), header=None)
    return _process_dataframe(df)

@st.cache_data(show_spinner=False, ttl=3600, max_entries=20)
def _process_pasted_text(text: str):
    df = parse_pasted_data(text)
    if df is None or df.empty:
        return None
    return _process_dataframe(df)

# Default column indices (0-based) used for the automatic summary.
NAME_COL_IDX = 2    # cột 2 -> Tên hàng
QTY_COL_IDX = 4     # cột 4 -> Số lượng
AMOUNT_COL_IDX = 6  # cột 6 -> Thành tiền

# Display order of the summary table columns.
SUMMARY_COLUMNS = ['Tên hàng', 'Số lượng', 'Đơn giá', 'Thành tiền']
SUMMARY_NUMERIC_COLUMNS = ['Số lượng', 'Đơn giá', 'Thành tiền']

def create_auto_summary(df, name_idx=NAME_COL_IDX, qty_idx=QTY_COL_IDX, amount_idx=AMOUNT_COL_IDX):
    """
    Build the automatic summary used in the Summarize tab.

    Flow:
      - Group by `name_idx`   (Tên hàng)
      - Sum `qty_idx`         (Số lượng)
      - Sum `amount_idx`      (Thành tiền)
      - Add a calculated column Đơn giá = Thành tiền / Số lượng

    Column order in the result: Tên hàng, Số lượng, Đơn giá, Thành tiền.

    Returns:
        summary DataFrame, or None if the data doesn't have the required columns.
    """
    if df is None or df.empty:
        return None

    n_cols = len(df.columns)
    if max(name_idx, qty_idx, amount_idx) >= n_cols or min(name_idx, qty_idx, amount_idx) < 0:
        return None

    name_col = df.columns[name_idx]
    qty_col = df.columns[qty_idx]
    amount_col = df.columns[amount_idx]

    work = df[[name_col, qty_col, amount_col]].copy()
    work.columns = ['Tên hàng', 'Số lượng', 'Thành tiền']

    # Ensure the quantity / amount columns are numeric.
    work['Số lượng'] = pd.to_numeric(work['Số lượng'], errors='coerce')
    work['Thành tiền'] = pd.to_numeric(work['Thành tiền'], errors='coerce')

    # Keep only rows that actually have a product name.
    work = work.dropna(subset=['Tên hàng'])
    if work.empty:
        return None

    summary = (
        work.groupby('Tên hàng', as_index=False)
        .agg({'Số lượng': 'sum', 'Thành tiền': 'sum'})
    )

    # Đơn giá = Thành tiền / Số lượng (guard against divide-by-zero).
    summary['Đơn giá'] = np.where(
        summary['Số lượng'] != 0,
        summary['Thành tiền'] / summary['Số lượng'],
        np.nan,
    )

    # Round numeric columns for display.
    summary['Số lượng'] = summary['Số lượng'].round(2)
    summary['Thành tiền'] = summary['Thành tiền'].round(2)
    summary['Đơn giá'] = summary['Đơn giá'].round(2)

    # Reorder so Đơn giá comes before Thành tiền.
    return summary[SUMMARY_COLUMNS]

# Main tabs for input method (Upload vs Paste)
input_tab1, input_tab2 = st.tabs(["📁 Upload", "📋 Paste"])

with input_tab1:
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose Excel file",
        type=['xls', 'xlsx'],
        label_visibility="collapsed"
    )
    
    if uploaded_file is not None:
        try:
            df = _process_uploaded_excel_bytes(uploaded_file.getvalue())
            
            if df is None or df.empty:
                st.error("❌ The uploaded file is empty!")
            else:
                # Store in session state so it can be reused across interactions
                st.session_state.df_processed = df
                
                # Simple success message
                st.success(f"✅ {len(df)} rows • {len(df.columns)} columns")
        
        except Exception as e:
            st.error(f"Error: {str(e)}")

with input_tab2:
    # Paste area
    pasted_text = st.text_area(
        "Paste your data here",
        height=200,
        placeholder="Paste data from Excel or any spreadsheet...\n(Tab, comma, or space separated)",
        label_visibility="collapsed"
    )
    
    if st.button("✨ Process", type="primary", use_container_width=True):
        if pasted_text:
            df = _process_pasted_text(pasted_text)
            
            if df is None:
                st.error("❌ Could not parse the data. Make sure it's properly formatted.")
            else:
                # Store in session state so it can be reused across interactions
                st.session_state.df_processed = df
                
                # Success message
                st.success(f"✅ {len(df)} rows • {len(df.columns)} columns")
        else:
            st.warning("⚠️ Please paste some data first")

# Read processed DataFrame from session state
df_processed = st.session_state.df_processed

# Display data if processed (from upload or paste)
if df_processed is not None:
    # Create tabs for data view
    tab1, tab2 = st.tabs(["📄 Raw Data", "📊 Summarize"])
            
    with tab1:
        # Display the raw dataframe - clean and simple
        st.dataframe(df_processed, use_container_width=True, height=400)
        
        # Quick column sum feature
        st.divider()
        
        # Get numeric columns
        numeric_cols = df_processed.select_dtypes(include=[np.number]).columns.tolist()
        
        if numeric_cols:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                selected_col = st.selectbox(
                    "Column to sum",
                    options=numeric_cols,
                    key='quick_sum_col',
                    label_visibility="visible"
                )
            
            with col2:
                if selected_col:
                    total = df_processed[selected_col].sum()
                    st.metric(
                        label="Total",
                        value=_format_metric_number(total),
                        delta=None
                    )
    
    with tab2:
        # Automatic summary:
        #   - Group by "Tên hàng"
        #   - Sum "Số lượng" and "Thành tiền"
        #   - Add Đơn giá = Thành tiền / Số lượng
        #   - Column order: Tên hàng, Số lượng, Đơn giá, Thành tiền
        n_data_cols = len(df_processed.columns)

        # Column mapping options. Defaults follow the standard layout but can be
        # adjusted if the data column order changes.
        default_name = NAME_COL_IDX if NAME_COL_IDX < n_data_cols else 0
        default_qty = QTY_COL_IDX if QTY_COL_IDX < n_data_cols else 0
        default_amount = AMOUNT_COL_IDX if AMOUNT_COL_IDX < n_data_cols else 0

        name_idx = st.session_state.get('map_name_idx', default_name)
        qty_idx = st.session_state.get('map_qty_idx', default_qty)
        amount_idx = st.session_state.get('map_amount_idx', default_amount)

        summary_df = create_auto_summary(df_processed, name_idx, qty_idx, amount_idx)

        if summary_df is None:
            st.warning(
                "Không tổng hợp được với cấu hình cột hiện tại. "
                "Hãy mở phần **⚙️ Tùy chỉnh cột** bên dưới để chọn lại cột."
            )
        else:
            styled = (
                summary_df.style
                .format({c: _format_table_number_grouped for c in SUMMARY_NUMERIC_COLUMNS})
                .hide(axis='index')
                .set_table_styles([
                    {
                        'selector': 'th',
                        'props': [
                            ('background-color', '#1E3A8A'),
                            ('color', '#FFFFFF'),
                            ('font-weight', '700'),
                            ('text-align', 'center'),
                            ('padding', '0.5rem 0.75rem'),
                        ],
                    },
                    {
                        'selector': 'td',
                        'props': [
                            ('padding', '0.4rem 0.75rem'),
                            ('border-bottom', '1px solid #E5E7EB'),
                        ],
                    },
                    {
                        'selector': 'td:nth-child(1)',
                        'props': [('text-align', 'left')],
                    },
                    {
                        'selector': 'td:nth-child(n+2)',
                        'props': [('text-align', 'right')],
                    },
                    {
                        'selector': 'table',
                        'props': [
                            ('border-collapse', 'collapse'),
                            ('width', '100%'),
                            ('font-size', '0.9rem'),
                        ],
                    },
                ])
            )
            # Render as HTML so the dark-blue bold header is guaranteed to show
            # (st.dataframe's canvas grid ignores header styles).
            st.markdown(
                f'<div style="overflow-x:auto;">{styled.to_html()}</div>',
                unsafe_allow_html=True,
            )

            st.write("")
            # Totals
            total_qty = summary_df['Số lượng'].sum()
            total_amount = summary_df['Thành tiền'].sum()
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Tổng số lượng", _format_metric_number_grouped(total_qty))
            with c2:
                st.metric("Tổng thành tiền", _format_metric_number_grouped(total_amount))

        # Column adjustment option (for when the data column order changes).
        st.divider()
        with st.expander("⚙️ Tùy chỉnh cột"):
            st.caption(
                "Chọn lại cột nếu thứ tự dữ liệu thay đổi. "
                "Số trong ngoặc là vị trí cột (bắt đầu từ 0)."
            )
            col_options = list(range(n_data_cols))

            def _col_label(i):
                # Show a short preview of the column's first non-null value.
                col = df_processed.columns[i]
                sample = df_processed[col].dropna()
                preview = str(sample.iloc[0]) if not sample.empty else ""
                if len(preview) > 18:
                    preview = preview[:18] + "…"
                return f"Cột {i}" + (f" ({preview})" if preview else "")

            st.selectbox(
                "📌 Tên hàng (group by)",
                options=col_options,
                index=name_idx if name_idx < n_data_cols else 0,
                format_func=_col_label,
                key='map_name_idx',
            )
            st.selectbox(
                "🔢 Số lượng (sum)",
                options=col_options,
                index=qty_idx if qty_idx < n_data_cols else 0,
                format_func=_col_label,
                key='map_qty_idx',
            )
            st.selectbox(
                "💰 Thành tiền (sum)",
                options=col_options,
                index=amount_idx if amount_idx < n_data_cols else 0,
                format_func=_col_label,
                key='map_amount_idx',
            )
            st.caption("Đơn giá = Thành tiền / Số lượng (tự động tính).")
else:
    st.info("👆 Upload a file or paste data to begin")


