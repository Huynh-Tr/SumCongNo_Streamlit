# Excel Data Summary Web App

A simple Streamlit web application that processes Excel files containing product sales data, automatically detects headers, and provides both raw and summarized views.

## Features

- 📁 Upload Excel files (`.xls` and `.xlsx` formats)
- 🔍 Automatic header detection and normalization
- 📊 Raw data table view with summary statistics
- 📈 Product summary with aggregated quantities and amounts
- 💰 Automatic price calculation (Amount / Quantity)
- 🎨 Clean, user-friendly interface

## Expected Data Format

Your Excel file should contain the following columns (in any order):
- **Date**: Transaction or record date
- **Product**: Product name or identifier
- **Unit**: Unit of measurement (e.g., kg, pcs, liters)
- **Quantity**: Number of units
- **Price**: Price per unit
- **Amount**: Total amount (Quantity × Price)

**Note**: The app can handle files with or without headers. If headers are missing, they will be automatically assigned.

## Installation

1. Clone this repository:
```bash
git clone <your-repository-url>
cd Webapp_Sum
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Running Locally

Run the Streamlit app with:
```bash
streamlit run streamlit_app.py
```

The app will open in your default web browser at `http://localhost:8501`

## Deployment

### Streamlit Cloud

1. Push this repository to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Sign in with GitHub
4. Click "New app"
5. Select your repository, branch (main), and main file path (`streamlit_app.py`)
6. Click "Deploy"

### Other Platforms

This app can be deployed to any platform that supports Streamlit applications, such as:
- Heroku
- AWS
- Google Cloud
- Azure

Make sure to:
- Install dependencies from `requirements.txt`
- Run the command: `streamlit run streamlit_app.py`

## Usage

1. Click the "Upload your Excel file" button
2. Select your Excel file (.xls or .xlsx)
3. View the data in two tabs:
   - **Raw Table**: Shows all uploaded data with summary statistics
   - **Product Summary**: Shows aggregated data grouped by product and unit

## Data Processing

The app performs the following operations:
- Detects and normalizes column headers
- Handles common variations (e.g., "Qty" → "Quantity", "Amt" → "Amount")
- Converts data to appropriate types (numeric for quantities/amounts, datetime for dates)
- Groups data by Product and Unit
- Calculates total Quantity and Amount per product
- Computes average Price as Total Amount / Total Quantity

## Requirements

- Python 3.8+
- streamlit>=1.28.0
- pandas>=2.0.0
- openpyxl>=3.1.0 (for .xlsx files)
- xlrd>=2.0.1 (for .xls files)

## License

This project is open source and available for use.

## Support

If you encounter any issues or have questions, please open an issue in the repository.

