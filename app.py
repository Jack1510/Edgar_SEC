
import streamlit as st
from pathlib import Path
import shutil
import os
import matplotlib.pyplot as plt
import seaborn as sns
from edgar_downloader import get_filing_types, download_edgar_filings
from mda_extractor import extract_mda_sections
from mda_analyzer import analyze_mda_streamlit


def plot_comprehensive_analysis(df):
    """Plot all financial metrics in a comprehensive dashboard"""
    if len(df) < 2:
        st.warning("Insufficient data for comprehensive analysis (need at least 2 years)")
        return
    
    with st.expander("📊 Comprehensive Financial Analysis", expanded=True):
       
        fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
       
        ax1.plot(df.index, df['revenue_growth_pct'], marker='o', color='blue', label='Revenue Growth %')
        ax1.set_title('Revenue Growth Trend', fontsize=12)
        ax1.set_xlabel('Year')
        ax1.set_ylabel('Growth Percentage')
        ax1.grid(True, linestyle='--', alpha=0.6)
        
        
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


st.set_page_config(page_title="SEC EDGAR Analyzer Pro", layout="wide")
st.title("📊 Advanced SEC EDGAR Financial Analyzer")


tab1, tab2, tab3 = st.tabs(["🔍 Data Collection", "📂 MD&A Extraction", "📈 Advanced Analysis"])

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

with tab3:
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
                                'revenue_growth_pct': '{:.1f}%',
                                'net_margin_pct': '{:.1f}%',
                                'gross_margin_pct': '{:.1f}%',
                                'current_ratio': '{:.2f}',
                                'quick_ratio': '{:.2f}',
                                'debt_to_equity': '{:.2f}',
                                'rnd_to_revenue': '{:.2f}%'
                            }))
                        
                        
                        plot_comprehensive_analysis(df)
                    
                    else:
                        st.warning("No valid financial data extracted from the filings.")
            
            except Exception as e:
                st.error(f"Analysis failed: {str(e)}")
            finally:
                shutil.rmtree(temp_analyze_dir)