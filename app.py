import streamlit as st
from pathlib import Path
import shutil
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from edgar_downloader import get_filing_types, download_edgar_filings
from extract_financials import extract_financial_statements
from mda_extractor import extract_mda_sections
from mda_analyzer import analyze_mda_streamlit
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def setup_session():
    """Set up a requests session with the appropriate headers"""
    session = requests.Session()
    session.headers.update({'User-Agent': 'aman.wadgaonkar@gmail.com'})
    return session

def get_cik_lookup(ticker):
    """Get CIK from ticker using SEC API"""
    ticker = ticker.upper()
    session = setup_session()
    url = f"https://www.sec.gov/files/company_tickers.json"
    
    response = session.get(url)
    if response.status_code != 200:
        st.error(f"Failed to access SEC API: {response.status_code}")
        return None
        
    data = response.json()
    
    # The company_tickers.json file contains a dictionary with numerical keys
    for entry in data.values():
        if entry['ticker'] == ticker:
            cik = str(entry['cik_str']).zfill(10)
            return cik
    
    return None

def get_filing_urls(ticker, form_type, years_back=5):
    """Get URLs for 10-K or 10-Q filings"""
    try:
        cik = get_cik_lookup(ticker)
        if not cik:
            return []
            
        session = setup_session()
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        response = session.get(url)
        
        if response.status_code != 200:
            st.error(f"Failed to retrieve submission data: {response.status_code}")
            return []
            
        data = response.json()
        filings = data.get("filings", {}).get("recent", {})
        cutoff_date = (datetime.now() - timedelta(days=365 * years_back)).strftime('%Y-%m-%d')
        
        results = []
        for i in range(len(filings.get("form", []))):
            if filings["form"][i] == form_type:
                filing_date = filings["filingDate"][i]
                
                # Skip if filing is older than cutoff
                if filing_date < cutoff_date:
                    continue
                    
                accession = filings["accessionNumber"][i].replace("-", "")
                
                # If primaryDocument is available, use it
                if "primaryDocument" in filings and i < len(filings["primaryDocument"]):
                    doc_name = filings["primaryDocument"][i]
                    if doc_name:  # Only use if not empty
                        url = f"https://www.sec.gov/Archives/edgar/data/{str(int(cik))}/{accession}/{doc_name}"
                        results.append((filing_date, url))
                        continue
                
                # Otherwise, get the main document from index.json
                try:
                    doc_url = get_10k_html_url(int(cik), accession)
                    if doc_url:
                        results.append((filing_date, doc_url))
                except Exception as e:
                    st.warning(f"Could not fetch document URL for {filing_date} filing: {str(e)}")
        
        return results
    except Exception as e:
        st.error(f"Error in fetching filing URLs: {str(e)}")
        return []

def get_10k_html_url(cik, accession):
    """Get the HTML URL for a specific filing document"""
    session = setup_session()
    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/index.json"
    response = session.get(url)
    
    if response.status_code != 200:
        return None
        
    data = response.json()
    files = data.get('directory', {}).get('item', [])
    
    # Find the main document
    main_docs = []
    for file in files:
        name = file.get('name', '').lower()
        if name.endswith('.htm') or name.endswith('.html'):
            # Add to list with priority
            priority = 1
            if '10k' in name or '10-k' in name or '10q' in name or '10-q' in name:
                priority = 0
            main_docs.append((priority, name))
    
    # Sort by priority (0 = highest)
    main_docs.sort()
    
    if not main_docs:
        return None
    
    # Get the highest priority document
    main_doc = main_docs[0][1]
    file_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{main_doc}"
    return file_url

# Streamlit App Config
st.set_page_config(page_title="SEC Filings Explorer", layout="wide")
st.title("📄 SEC Filings Data Extractor")

def plot_comprehensive_analysis(df):
    """Plot all financial metrics in a comprehensive dashboard"""
    if len(df) < 2:
        st.warning("Insufficient data for comprehensive analysis (need at least 2 years)")
        return
    
    with st.expander("📊 Comprehensive Financial Analysis", expanded=True):
       
        fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        if 'revenue_growth_pct' in df.columns:
            ax1.plot(df.index, df['revenue_growth_pct'], marker='o', color='blue', label='Revenue Growth %')
            ax1.set_title('Revenue Growth Trend', fontsize=12)
            ax1.set_xlabel('Year')
            ax1.set_ylabel('Growth Percentage')
            ax1.grid(True, linestyle='--', alpha=0.6)
        
        if 'net_margin_pct' in df.columns:
            ax2.plot(df.index, df['net_margin_pct'], marker='s', color='green', label='Net Margin %')
            if 'gross_margin_pct' in df.columns:
                ax2.plot(df.index, df['gross_margin_pct'], marker='^', color='orange', label='Gross Margin %')
            ax2.set_title('Profitability Trends', fontsize=12)
            ax2.set_xlabel('Year')
            ax2.set_ylabel('Margin Percentage')
            ax2.legend()
            ax2.grid(True, linestyle='--', alpha=0.6)
        
        st.pyplot(fig1)
        plt.close(fig1)

        fig2, (ax3, ax4) = plt.subplots(1, 2, figsize=(16, 6))
        
        if 'current_ratio' in df.columns:
            ax3.plot(df.index, df['current_ratio'], marker='o', color='purple', label='Current Ratio')
        if 'quick_ratio' in df.columns:
            ax3.plot(df.index, df['quick_ratio'], marker='s', color='red', label='Quick Ratio')
        ax3.set_title('Liquidity Ratios', fontsize=12)
        ax3.set_xlabel('Year')
        ax3.set_ylabel('Ratio Value')
        ax3.legend()
        ax3.grid(True, linestyle='--', alpha=0.6)
        
        if 'rnd_to_revenue' in df.columns:
            ax4.plot(df.index, df['rnd_to_revenue'], marker='o', color='brown', label='R&D/Revenue')
        if 'asset_turnover' in df.columns:
            ax4.plot(df.index, df['asset_turnover'], marker='s', color='teal', label='Asset Turnover')
        ax4.set_title('Efficiency Ratios', fontsize=12)
        ax4.set_xlabel('Year')
        ax4.set_ylabel('Percentage')
        ax4.legend()
        ax4.grid(True, linestyle='--', alpha=0.6)
        
        st.pyplot(fig2)
        plt.close(fig2)

        fig3, (ax5, ax6) = plt.subplots(1, 2, figsize=(16, 6))
        
        if 'rnd_to_revenue' in df.columns:
            ax5.plot(df.index, df['rnd_to_revenue'], marker='o', color='navy', label='R&D/Revenue')
        if 'capex_to_revenue' in df.columns:
            ax5.plot(df.index, df['capex_to_revenue'], marker='s', color='gray', label='Capex/Revenue')
        ax5.set_title('Investment Ratios', fontsize=12)
        ax5.set_xlabel('Year')
        ax5.set_ylabel('Percentage of Revenue')
        ax5.legend()
        ax5.grid(True, linestyle='--', alpha=0.6)
        
        if 'debt_to_equity' in df.columns:
            ax6.plot(df.index, df['debt_to_equity'], marker='o', color='darkred', label='Debt/Equity')
        if 'interest_coverage' in df.columns:
            ax6.plot(df.index, df['interest_coverage'], marker='s', color='darkgreen', label='Interest Coverage')
        ax6.set_title('Leverage Ratios', fontsize=12)
        ax6.set_xlabel('Year')
        ax6.set_ylabel('Ratio Value')
        ax6.legend()
        ax6.grid(True, linestyle='--', alpha=0.6)
        
        st.pyplot(fig3)
        plt.close(fig3)

        if len(df) >= 3:
            fig4, ax7 = plt.subplots(figsize=(12, 8))
            metrics = [
                'revenue_growth_pct', 'net_margin_pct', 
                'rnd_to_revenue', 'current_ratio',
                'debt_to_equity', 'asset_turnover'
            ]
            metrics = [m for m in metrics if m in df.columns]
            
            if len(metrics) > 1:
                sns.heatmap(
                    df[metrics].corr(), 
                    annot=True, 
                    cmap='coolwarm',
                    annot_kws={"size": 10}, 
                    vmin=-1, 
                    vmax=1,
                    ax=ax7
                )
                ax7.set_title("Financial Metric Correlations", fontsize=14)
                plt.xticks(rotation=45, fontsize=10)
                plt.yticks(rotation=0, fontsize=10)
                st.pyplot(fig4)
                plt.close(fig4)

# Main App
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Data Collection", "🌐 URL Fetcher", "📂 MD&A Extraction", "📈 Advanced Analysis", "Extract Financials"])

with tab1:
    st.header("📦 SEC EDGAR Filings Downloader")
    st.markdown("Enter a **Ticker** (e.g. `AAPL`) or a **CIK** (e.g. `320193`) and download filings as a ZIP.")

    user_input = st.text_input("Ticker or CIK", key="download_input").strip()
    filing_type = st.selectbox("Select Filing Type", get_filing_types(), key="download_type")
    years_back = st.slider("Years Back", 1, 20, 5, key="download_years")

    if st.button("📥 Fetch Filings", key="download_button"):
        if not user_input:
            st.warning("⚠️ Please enter a ticker or CIK.")
        else:
            ticker, cik = (None, user_input) if user_input.isdigit() else (user_input.upper(), None)

            if os.path.exists("edgar_data"):
                shutil.rmtree("edgar_data")
            Path("edgar_data").mkdir(exist_ok=True)

            with st.spinner("Fetching filings and creating ZIP..."):
                try:
                    success, count, data_dir = download_edgar_filings(
                        ticker=ticker,
                        cik=cik,
                        filing_type=filing_type,
                        years_back=years_back
                    )

                    if not success or count == 0:
                        st.error("❌ No filings found. Please provide a correct ticker name or CIK number.")
                    else:
                        zip_path = shutil.make_archive("edgar_filings", 'zip', data_dir)
                        with open(zip_path, "rb") as f:
                            st.download_button(
                                label="⬇️ Download ZIP",
                                data=f,
                                file_name="edgar_filings.zip",
                                mime="application/zip",
                                key="download_zip"
                            )
                        st.success(f"✅ Successfully downloaded {count} filings!")
                except Exception as e:
                    st.error(f"💥 Something went wrong:\n\n`{str(e)}`")

with tab2:
    st.header("🌐 SEC Filing URL Fetcher")
    st.markdown("Get HTML URLs for 10-K and 10-Q filings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        ticker_for_urls = st.text_input("Enter Ticker Symbol (e.g., AAPL)", key="html_url_ticker").strip().upper()
        form_type = st.selectbox("Select Filing Type for URLs", ["10-K", "10-Q"], key="html_url_type")
        url_years = st.slider("Number of Years to Search", 1, 10, 3, key="html_url_years")
    
    with col2:
        st.markdown("### Base URL Configuration")
        base_url = st.text_input(
            "Enter Base URL for fetch_data.py",
            value="https://www.sec.gov/Archives/edgar/data/",
            key="base_url_input"
        )

    if st.button("🔎 Fetch Filing URLs", key="html_url_button"):
        if not ticker_for_urls:
            st.warning("⚠️ Please enter a ticker symbol.")
        else:
            with st.spinner(f"Fetching {form_type} filings for {ticker_for_urls}..."):
                urls = get_filing_urls(ticker_for_urls, form_type, url_years)
                
                if urls:
                    df_urls = pd.DataFrame(urls, columns=["Filing Date", "Filing URL"])
                    df_urls = df_urls.sort_values(by="Filing Date", ascending=False)
                    
                    # Add button to copy URLs to clipboard
                    if not df_urls.empty:
                        st.dataframe(df_urls)
                        st.download_button(
                            label="📥 Download URLs as CSV",
                            data=df_urls.to_csv(index=False),
                            file_name=f"{ticker_for_urls}_{form_type}_urls.csv",
                            mime="text/csv"
                        )
                    st.success(f"✅ Found {len(df_urls)} {form_type} filings for {ticker_for_urls}.")
                else:
                    st.warning(f"No {form_type} filings found for {ticker_for_urls} in the last {url_years} years.")

with tab3:
    st.header("🔍 Extract MD&A Sections")
    st.markdown("Upload HTML filings or use previously downloaded files to extract Management Discussion & Analysis (Item 7) sections.")

    uploaded_files = st.file_uploader("Upload HTML filings", type=["html", "htm"], accept_multiple_files=True)
    use_existing = st.checkbox("Use files from previous download (in 'edgar_data' folder)", value=True)

    if st.button("Extract MD&A", key="extract_button"):
        if not uploaded_files and not use_existing:
            st.warning("⚠️ Please upload files or check the box to use existing files.")
        else:
            mda_output_dir = "mda_output"
            if os.path.exists(mda_output_dir):
                shutil.rmtree(mda_output_dir)
            os.makedirs(mda_output_dir, exist_ok=True)

            if uploaded_files:
                temp_dir = Path("temp_uploads")
                temp_dir.mkdir(exist_ok=True)
                for uploaded_file in uploaded_files:
                    with open(temp_dir / uploaded_file.name, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                extracted_count = extract_mda_sections(str(temp_dir), mda_output_dir)
                shutil.rmtree(temp_dir)

            if use_existing and os.path.exists("edgar_data"):
                existing_count = extract_mda_sections("edgar_data", mda_output_dir)
                extracted_count = extracted_count + existing_count if 'extracted_count' in locals() else existing_count

            if ('extracted_count' in locals()) and extracted_count > 0:
                st.success(f"✅ Extracted {extracted_count} MD&A section(s).")
                mda_zip_path = shutil.make_archive("mda_sections", 'zip', mda_output_dir)
                with open(mda_zip_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Download MD&A Sections",
                        data=f,
                        file_name="mda_sections.zip",
                        mime="application/zip",
                        key="download_mda"
                    )
            else:
                st.warning("⚠️ No MD&A sections found to extract.")

with tab4:
    st.header("Comprehensive Financial Analysis")
    st.markdown("""
    **Analyze multiple financial dimensions:**
    - Revenue growth and profitability trends
    - Liquidity and efficiency ratios
    - Investment and R&D spending
    - Debt and leverage metrics
    - Cross-metric correlations
    """)
    
    analyze_uploaded = st.file_uploader("Upload MD&A text files", type=["txt"], accept_multiple_files=True)
    use_extracted = st.checkbox("Use previously extracted MD&A files (from 'mda_output' folder)", value=True)
    
    if st.button("Run Comprehensive Analysis", key="comp_analysis"):
        if not analyze_uploaded and not use_extracted:
            st.warning("⚠️ Please upload files or check the box to use existing files.")
        else:
            temp_analyze_dir = Path("temp_analysis")
            temp_analyze_dir.mkdir(exist_ok=True)
            
            if analyze_uploaded:
                for uploaded_file in analyze_uploaded:
                    with open(temp_analyze_dir / uploaded_file.name, "wb") as f:
                        f.write(uploaded_file.getbuffer())
            
            if use_extracted and os.path.exists("mda_output"):
                for mda_file in Path("mda_output").glob("*.txt"):
                    shutil.copy(mda_file, temp_analyze_dir)
            
            try:
                with st.spinner("Performing comprehensive financial analysis..."):
                    df = analyze_mda_streamlit(str(temp_analyze_dir))
                    
                    if df is not None and not df.empty:
                        df.index = df.index.astype(str)
                        
                        with st.expander("View Raw Data"):
                            st.dataframe(df.style.format({
                                col: '{:.1f}%' if '%' in col else '{:.2f}' 
                                for col in df.columns
                                if df[col].dtype in ['float64', 'int64']
                            }))
                        
                        plot_comprehensive_analysis(df)
                    
                    else:
                        st.warning("No valid financial data extracted from the filings.")
            
            except Exception as e:
                st.error(f"Analysis failed: {str(e)}")
            finally:
                shutil.rmtree(temp_analyze_dir)
with tab5:
    st.header("📊 Extract Financial Statements")
    st.markdown("""
    Upload HTML filings or use previously downloaded files to extract:
    - Balance Sheet
    - Income Statement
    - Cash Flow Statement
    """)

    # File upload section
    uploaded_files = st.file_uploader(
        "Upload HTML filings", 
        type=["html", "htm"], 
        accept_multiple_files=True, 
        key="upload_financials"
    )
    
    # Path selection section
    st.markdown("### OR Use Existing Files")
    existing_path = st.text_input(
        "Path to downloaded filings (e.g., 'sec_data/AAPL/10-K')",
        value="sec_data/AAPL/10-K",
        key="existing_financial_path"
    )
    
    if st.button("Extract Financial Statements", key="extract_financials_button"):
        if not uploaded_files and not existing_path:
            st.warning("⚠️ Please upload files or provide a path to existing files.")
        else:
            financial_output_dir = "extracted_financials"
            
            # Clear existing output directory
            if os.path.exists(financial_output_dir):
                shutil.rmtree(financial_output_dir)
            os.makedirs(financial_output_dir, exist_ok=True)
            
            extracted_count = 0
            
            # Process uploaded files
            if uploaded_files:
                temp_dir = Path("temp_financial_uploads")
                temp_dir.mkdir(exist_ok=True)
                
                for uploaded_file in uploaded_files:
                    file_path = temp_dir / uploaded_file.name
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                
                extracted_count += extract_financial_statements(str(temp_dir), financial_output_dir)
                shutil.rmtree(temp_dir)
            
            # Process existing files
            if existing_path and os.path.exists(existing_path):
                extracted_count += extract_financial_statements(existing_path, financial_output_dir)
            
            # Display results
            if extracted_count > 0:
                st.success(f"✅ Extracted financial data from {extracted_count} file(s).")
                
                # Create zip archive of extracted data
                zip_path = shutil.make_archive("financial_statements", 'zip', financial_output_dir)
                
                # Show download button and preview
                with open(zip_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Download Extracted Financials",
                        data=f,
                        file_name="financial_statements.zip",
                        mime="application/zip",
                        key="download_financials"
                    )
                
                # Show preview of extracted files
                st.markdown("### Extracted Files Preview")
                extracted_files = list(Path(financial_output_dir).glob("*.csv"))
                if extracted_files:
                    sample_file = extracted_files[0]
                    df = pd.read_csv(sample_file)
                    st.write(f"Sample from {sample_file.name}:")
                    st.dataframe(df.head())
                else:
                    st.warning("No CSV files were created during extraction.")
            else:
                st.warning("⚠️ No financial statements found to extract.")