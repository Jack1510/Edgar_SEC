import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import re
from collections import defaultdict
from pathlib import Path
import streamlit as st
from scipy.stats import linregress

class FinancialStatementAnalyzer:
    def __init__(self):
        self.metric_patterns = {
            'revenue': [
                r"(?:total\s+)?(?:net\s+)?(?:sales|revenue)[^\$]*\$?\s*([\d,\.]+)\s*(?:million|billion|M|B)?",
                r"revenue\s+from\s+.*\$?\s*([\d,\.]+)",
                r"consolidated\s+.*revenue[^\$]*\$?\s*([\d,\.]+)"
            ],
            'gross_margin_pct': [
                r"gross\s+(?:margin|profit)\s*(?:ratio|percentage|percent|%)?\s*(?:of\s+[^\d]*)?(\d{1,3}\.\d{1,2})[\s%]",
                r"gross\s+profit\s+margin.*?(\d{1,3}\.\d{1,2})[\s%]"
            ],
            'net_income': [
                r"net\s+(?:income|earnings|profit)\s*(?:attributable\s+to[^\$]*)?\$?\s*([\d,\.]+)\s*(?:million|billion|M|B)?",
                r"consolidated\s+net\s+.*\$?\s*([\d,\.]+)"
            ],
            'operating_income': [
                r"operating\s+(?:income|profit|earnings)[^\$]*\$?\s*([\d,\.]+)\s*(?:million|billion|M|B)?",
                r"income\s+from\s+operations[^\$]*\$?\s*([\d,\.]+)"
            ],
            'total_assets': [
                r"total\s+assets[^\$]*\$?\s*([\d,\.]+)\s*(?:million|billion|M|B)?",
                r"consolidated\s+.*assets[^\$]*\$?\s*([\d,\.]+)"
            ],
            'total_liabilities': [
                r"total\s+liabilities[^\$]*\$?\s*([\d,\.]+)\s*(?:million|billion|M|B)?",
                r"consolidated\s+.*liabilities[^\$]*\$?\s*([\d,\.]+)"
            ],
            'current_assets': [
                r"current\s+assets[^\$]*\$?\s*([\d,\.]+)\s*(?:million|billion|M|B)?",
                r"total\s+current\s+assets[^\$]*\$?\s*([\d,\.]+)"
            ],
            'current_liabilities': [
                r"current\s+liabilities[^\$]*\$?\s*([\d,\.]+)\s*(?:million|billion|M|B)?",
                r"total\s+current\s+liabilities[^\$]*\$?\s*([\d,\.]+)"
            ],
            'cash_equivalents': [
                r"cash\s+and\s+cash\s+equivalents[^\$]*\$?\s*([\d,\.]+)\s*(?:million|billion|M|B)?",
                r"cash\s+equivalents[^\$]*\$?\s*([\d,\.]+)"
            ],
            'rnd': [
                r"research\s+and\s+development[^\$]*\$?\s*([\d,\.]+)\s*(?:million|billion|M|B)?",
                r"r\s*&\s*d[^\$]*\$?\s*([\d,\.]+)"
            ],
            'ebitda': [
                r"ebitda[^\$]*\$?\s*([\d,\.]+)\s*(?:million|billion|M|B)?",
                r"earnings\s+before\s+interest.*tax.*depreciation[^\$]*\$?\s*([\d,\.]+)"
            ]
        }

    def clean_value(self, value_str):
        """Convert string values to float with unit handling"""
        if not value_str:
            return None

        
        value_str = value_str.replace(',', '').replace('$', '').strip().lower()

        
        multiplier = 1
        if 'billion' in value_str or 'b' in value_str:
            multiplier = 1e9
            value_str = re.sub(r'(billion|b)', '', value_str)
        elif 'million' in value_str or 'm' in value_str:
            multiplier = 1e6
            value_str = re.sub(r'(million|m)', '', value_str)

        try:
            return float(value_str) * multiplier
        except ValueError:
            return None

    def extract_metric(self, text, patterns):
        """Try multiple patterns to extract a metric"""
        text = text.replace('\n', ' ').replace('\r', ' ').lower()
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                
                cleaned = self.clean_value(matches[-1])
                if cleaned is not None:
                    return cleaned
        return None

    def extract_all_metrics(self, text):
        """Extract all financial metrics from text"""
        results = {}
        text = self.preprocess_text(text)
        
        for metric, patterns in self.metric_patterns.items():
            value = self.extract_metric(text, patterns)
            if value is not None:
                
                if metric.endswith('_pct'):
                    results[metric] = value
                else:
                    results[metric] = value / 1e9
        return results

    def preprocess_text(self, text):
        """Clean and normalize text for better pattern matching"""
       
        text = re.sub(r'<[^>]+>', ' ', text)
        
        text = re.sub(r'\s+', ' ', text)
        
        text = re.sub(r'(\d),(\d)', r'\1\2', text)
        return text.lower()

    def calculate_ratios(self, df):
        """Calculate financial ratios with safe division"""
       
        if 'gross_margin_pct' in df and 'revenue' in df:
            df['gross_margin'] = df['revenue'] * df['gross_margin_pct'] / 100

        if 'operating_income' in df and 'revenue' in df:
            df['operating_margin_pct'] = (df['operating_income'] / df['revenue'].replace(0, np.nan)) * 100

        if 'net_income' in df and 'revenue' in df:
            df['net_margin_pct'] = (df['net_income'] / df['revenue'].replace(0, np.nan)) * 100

        if 'net_income' in df and 'total_assets' in df:
            df['roa'] = (df['net_income'] / df['total_assets'].replace(0, np.nan)) * 100

        if all(col in df for col in ['net_income', 'total_assets', 'total_liabilities']):
            df['roe'] = (df['net_income'] / (df['total_assets'] - df['total_liabilities']).replace(0, np.nan)) * 100


        if 'current_assets' in df and 'current_liabilities' in df:
            df['current_ratio'] = df['current_assets'] / df['current_liabilities'].replace(0, np.nan)

        if all(col in df for col in ['current_assets', 'cash_equivalents', 'current_liabilities']):
            df['quick_ratio'] = (df['cash_equivalents'] / df['current_liabilities'].replace(0, np.nan))


        if 'rnd' in df and 'revenue' in df:
            df['rnd_to_revenue'] = (df['rnd'] / df['revenue'].replace(0, np.nan)) * 100

        
        for metric in ['revenue', 'net_income', 'operating_income']:
            if metric in df:
                df[f'{metric}_growth_pct'] = df[metric].pct_change() * 100

        return df

def analyze_mda_streamlit(mda_dir):
    """Main analysis function for Streamlit"""
    analyzer = FinancialStatementAnalyzer()
    financial_data = defaultdict(dict)
    
    mda_dir = Path(mda_dir)
    processed_files = 0
    
    for txt_file in mda_dir.glob("*.txt"):
        try:
            
            year_match = re.search(r'(20\d{2})', txt_file.stem)
            if not year_match:
                st.warning(f"Could not determine year for file: {txt_file.name}")
                continue
                
            year = int(year_match.group(1))
            
            with open(txt_file, 'r', encoding='utf-8', errors='ignore') as file:
                text = file.read()
                
            if len(text) < 1000:  
                st.warning(f"File too small to analyze: {txt_file.name}")
                continue
                
            extracted = analyzer.extract_all_metrics(text)
            if extracted:
                financial_data[year] = extracted
                processed_files += 1
                
        except Exception as e:
            st.error(f"Error processing {txt_file.name}: {str(e)}")
    
    if not financial_data:
        st.error("""
        ❌ No financial data extracted from MD&A sections. Possible reasons:
        1. The files don't contain standard financial statements
        2. The text format is not being parsed correctly
        3. The files are not 10-K MD&A sections
        """)
        return None

    st.success(f"✅ Successfully processed {processed_files} files with financial data")
    
    
    df = pd.DataFrame.from_dict(financial_data, orient='index')
    df.index.name = 'Year'
    df = df.sort_index()
    
   
    df = analyzer.calculate_ratios(df)
    
    
    with st.expander("View Extracted Raw Data"):
        st.dataframe(df.style.format("{:,.2f}"))
    
    
    required_metrics = ['revenue', 'net_income', 'total_assets']
    missing_metrics = [m for m in required_metrics if m not in df.columns]
    
    if missing_metrics:
        st.warning(f"⚠️ Warning: Could not extract these critical metrics: {', '.join(missing_metrics)}")
    
    return df