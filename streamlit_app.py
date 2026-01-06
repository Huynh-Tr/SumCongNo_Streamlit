import streamlit as st
import pandas as pd
from io import BytesIO, StringIO
import numpy as np

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
    # Calculate null threshold (80% or more nulls = remove)
    null_threshold = 0.8
    
    # Remove rows with too many nulls
    row_null_ratio = df.isna().sum(axis=1) / len(df.columns)
    df = df[row_null_ratio < null_threshold].reset_index(drop=True)
    
    # Remove completely empty columns
    col_null_ratio = df.isna().sum(axis=0) / len(df)
    df = df.loc[:, col_null_ratio < 1.0]
    
    # Remove leading empty rows (rows before first row with significant data)
    for idx in range(len(df)):
        if df.iloc[idx].notna().sum() >= 3:  # At least 3 non-null values
            df = df.iloc[idx:].reset_index(drop=True)
            break
    
    # Remove trailing empty rows
    for idx in range(len(df)-1, -1, -1):
        if df.iloc[idx].notna().sum() >= 3:  # At least 3 non-null values
            df = df.iloc[:idx+1].reset_index(drop=True)
            break
    
    return df

def simplify_dataframe(df):
    """
    Simplify DataFrame by:
    1. Removing completely empty columns
    2. Naming columns as Col_0, Col_1, etc.
    Returns: simplified DataFrame
    """
    # Remove completely empty columns
    df = df.loc[:, df.notna().any()]
    
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
            # Attempt numeric conversion
            converted = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
            # If at least 50% of non-null values become numeric, keep conversion
            if converted.notna().sum() >= 0.5 * df[col].notna().sum() and converted.notna().sum() > 0:
                df[col] = converted
    return df

def parse_pasted_data(text):
    """
    Parse pasted text data into DataFrame.
    Supports: tab-separated, comma-separated, or space-separated.
    Returns: DataFrame or None if parsing fails
    """
    if not text or not text.strip():
        return None
    
    try:
        # Try tab-separated first (most common from Excel copy)
        if '\t' in text:
            df = pd.read_csv(StringIO(text), sep='\t', header=None)
        # Try comma-separated
        elif ',' in text:
            df = pd.read_csv(StringIO(text), sep=',', header=None)
        # Try space/whitespace separated
        else:
            df = pd.read_csv(StringIO(text), sep=r'\s+', header=None, engine='python')
        
        return df if not df.empty else None
    except Exception as e:
        return None

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
            # Read the Excel file without headers
            df = pd.read_excel(uploaded_file, header=None)
            
            if df.empty:
                st.error("❌ The uploaded file is empty!")
            else:
                # Show original dimensions
                original_shape = df.shape
                
                # Clean empty rows and columns
                df = clean_empty_rows_and_columns(df)
                
                # Simplify DataFrame - remove empty columns and rename
                df = simplify_dataframe(df)

                # Try to convert numeric-like columns
                df = convert_numeric_columns(df)
                
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
            df = parse_pasted_data(pasted_text)
            
            if df is None:
                st.error("❌ Could not parse the data. Make sure it's properly formatted.")
            else:
                # Clean empty rows and columns
                df = clean_empty_rows_and_columns(df)
                
                # Simplify DataFrame
                df = simplify_dataframe(df)

                # Try to convert numeric-like columns
                df = convert_numeric_columns(df)
                
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
                        value=f"{total:,.2f}",
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
                    st.dataframe(summary_df, use_container_width=True, height=350)
                    
                    # Simple totals
                    if len(sum_cols) <= 3:
                        cols = st.columns(len(sum_cols))
                        for idx, col in enumerate(sum_cols):
                            with cols[idx]:
                                total = summary_df[col].sum()
                                st.metric(col, f"{total:,.0f}")
else:
    st.info("👆 Upload a file or paste data to begin")


