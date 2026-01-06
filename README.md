# SumCongNo Streamlit

Mobile-friendly Streamlit app to analyze Excel or pasted data. Optimized for iPhone: upload or paste, view raw data, quick sum, and build custom group-by summaries.

## Features
- 📁 Upload .xls / .xlsx
- 📋 Paste data from clipboard (tab/comma/space separated)
- 🧹 Auto-clean empty rows/columns
- 🔤 Simple column naming (Col_0, Col_1, …)
- 📄 Raw Data tab with quick sum card
- 📊 Custom Summary tab: choose group-by columns, sum columns, and optional ratio column
- 🎨 iPhone-optimized UI (centered layout, large buttons, clean typography)

## Quick Start
`ash
git clone https://github.com/Huynh-Tr/SumCongNo_Streamlit.git
cd Webapp_Sum
pip install -r requirements.txt
streamlit run streamlit_app.py
`
Open http://localhost:8501

## How to Use
1) **Input**  
   - Upload tab: drop or browse Excel file  
   - Paste tab: paste data copied from Excel/Sheets/Numbers, then click **Process**

2) **Raw Data tab**  
   - View full table  
   - Select a numeric column to see its total in a card

3) **Custom Summary tab**  
   - Multi-select **Group By** columns (any columns)  
   - Multi-select **Sum** columns (numeric only)  
   - Optional **Calculate**: pick numerator & denominator (creates ratio column)  
   - Click **✨ Create Summary** to see grouped results and totals

## Notes
- Columns are auto-renamed to Col_0, Col_1, ... for simplicity
- Parsing supports tab/comma/space-separated pasted data
- Streamlit config in .streamlit/config.toml

## Requirements
- Python 3.8+
- streamlit>=1.28.0
- pandas>=2.0.0
- openpyxl>=3.1.0
- xlrd>=2.0.1

## License
MIT (see LICENSE)
