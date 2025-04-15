from sec_edgar_downloader import Downloader
from datetime import datetime
from pathlib import Path
from enum import Enum

# Filing types enum
class FilingType(str, Enum):
    FORM_10K = "10-K"
    FORM_10Q = "10-Q"
    FORM_8K = "8-K"
    FORM_S1 = "S-1"
    FORM_13F = "13F-HR"
    FORM_4 = "4"
    FORM_DEF14A = "DEF 14A"
    FORM_10KSB = "10-KSB"
    FORM_10QSB = "10-QSB"
    FORM_20F = "20-F"
    FORM_40F = "40-F"
    FORM_6K = "6-K"
    FORM_10 = "10"
    FORM_8A = "8-A"
    FORM_485BPOS = "485BPOS"
    FORM_497 = "497"
    FORM_N1A = "N-1A"
    FORM_N2 = "N-2"
    FORM_NT10K = "NT 10-K"
    FORM_NT10Q = "NT 10-Q"

def get_filing_types():
    return [filing.value for filing in FilingType]

def download_edgar_filings(ticker: str, filing_type: str, years_back: int, cik: str = None):
    data_dir = Path("edgar_data")
    data_dir.mkdir(exist_ok=True)

    dl = Downloader("MyCompany", "youremail@example.com", data_dir)

    today = datetime.now().year
    start_year = today - years_back

    try:
        identifier = cik if cik else ticker
        num_downloaded = dl.get(
            filing_type,
            identifier,
            after=f"{start_year}-01-01",
            before=f"{today}-12-31",
            download_details=True
        )
        return True, num_downloaded, data_dir
    except Exception as e:
        print(f"Download failed: {e}")
        return False, 0, None
