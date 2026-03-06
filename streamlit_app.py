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

def create_custom_summary(df, groupby_cols, sum_cols, calc_col1=None, calc_col2=None):
    """
    Create a custom summary based on user-selected columns.
    
    Args:
        df: DataFrame
        groupby_cols: List of columns to group by
        sum_cols: List of columns to sum
        calc_col1: Optional - numerator column for calculated column
        calc_col2: Optional - denominator column for calculated column
    
    Returns:
        summary DataFrame
    """
    if not groupby_cols or not sum_cols:
        return None
    
    # Create aggregation dictionary
    agg_dict = {col: 'sum' for col in sum_cols}
    
    # Group and aggregate
    summary = df.groupby(groupby_cols).agg(agg_dict).reset_index()
    
    # Create calculated column if requested
    if calc_col1 and calc_col2 and calc_col1 in sum_cols and calc_col2 in sum_cols:
        summary[f'{calc_col1}_div_{calc_col2}'] = summary[calc_col1] / summary[calc_col2]
        summary[f'{calc_col1}_div_{calc_col2}'] = summary[f'{calc_col1}_div_{calc_col2}'].round(2)
    
    # Round numeric columns
    for col in sum_cols:
        if pd.api.types.is_numeric_dtype(summary[col]):
            summary[col] = summary[col].round(2)
    
    return summary

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
    tab1, tab2 = st.tabs(["📄 Raw Data", "📊 Custom Summary"])
            
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
        # Get all columns
        all_cols = df_processed.columns.tolist()
        numeric_cols = df_processed.select_dtypes(include=[np.number]).columns.tolist()
        
        # Group By
        st.markdown("**📌 Group By**")
        groupby_cols = st.multiselect(
            "Select columns",
            options=all_cols,
            key='groupby_cols',
            label_visibility="collapsed"
        )
        
        # Sum
        st.markdown("**➕ Sum**")
        sum_cols = st.multiselect(
            "Select numeric columns",
            options=numeric_cols,
            key='sum_cols',
            label_visibility="collapsed"
        )
        
        # Calculated column
        calc_col1 = None
        calc_col2 = None
        if len(sum_cols) >= 2:
            st.markdown("**🧮 Calculate (Optional)**")
            col1, col2 = st.columns(2)
            with col1:
                calc_col1 = st.selectbox(
                    "Numerator",
                    options=['—'] + sum_cols,
                    key='calc_col1',
                    label_visibility="visible"
                )
            with col2:
                calc_col2 = st.selectbox(
                    "Denominator",
                    options=['—'] + sum_cols,
                    key='calc_col2',
                    label_visibility="visible"
                )
            calc_col1 = None if calc_col1 == '—' else calc_col1
            calc_col2 = None if calc_col2 == '—' else calc_col2
        
        # Create button
        if st.button("✨ Create Summary", type="primary", use_container_width=True):
            if not groupby_cols:
                st.warning("Select at least one column to group by")
            elif not sum_cols:
                st.warning("Select at least one column to sum")
            else:
                summary_df = create_custom_summary(
                    df_processed, groupby_cols, sum_cols, calc_col1, calc_col2
                )
                
                if summary_df is not None:
                    st.divider()
                    calc_col_name = (
                        f"{calc_col1}_div_{calc_col2}" if calc_col1 and calc_col2 else None
                    )
                    display_format_cols = [c for c in (sum_cols + ([calc_col_name] if calc_col_name else [])) if c in summary_df.columns]
                    if display_format_cols:
                        styled = summary_df.style.format(
                            {c: _format_table_number_grouped for c in display_format_cols}
                        )
                        st.dataframe(styled, use_container_width=True, height=350)
                    else:
                        st.dataframe(summary_df, use_container_width=True, height=350)
                    
                    # Simple totals
                    if len(sum_cols) <= 3:
                        cols = st.columns(len(sum_cols))
                        for idx, col in enumerate(sum_cols):
                            with cols[idx]:
                                total = summary_df[col].sum()
                                st.metric(col, _format_metric_number_grouped(total))
else:
    st.info("👆 Upload a file or paste data to begin")


