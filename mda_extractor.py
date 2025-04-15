import os
import re
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime

def extract_item_7_from_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    
    item7_link = None
    for a in soup.find_all('a'):
        text = a.get_text(strip=True).lower()
        if text.startswith(("item 7", "item7", "item 7", "management's discussion")):
            item7_link = a.get('href')
            break

    if not item7_link or not item7_link.startswith("#"):
        return "Item 7 not found (no valid anchor link)"

    item7_section = soup.find(id=item7_link.lstrip("#"))
    if not item7_section:
        return "Item 7 section not found"

    content = []
    current_element = item7_section.find_next()
    while current_element:
        if current_element.name == 'a' and 'item' in current_element.get_text(strip=True).lower():
            break
        content.append(current_element.get_text(separator=' ', strip=True))
        current_element = current_element.find_next()

    return " ".join(content)

def clean_text(text):
    text = re.sub(r'\s+', ' ', text.replace('\xa0', ' ')).strip()
    return re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)  

def extract_fiscal_year_from_content(content, filename):

    fiscal_year_patterns = [
        r'fiscal\s+year\s+ended\s+.*?\b(20\d{2})\b',
        r'for\s+the\s+year\s+ended\s+.*?\b(20\d{2})\b',
        r'for\s+fiscal\s+(20\d{2})',
        r'fiscal\s+(20\d{2})',
        r'FY\s*(20\d{2})',
        r'\b(20\d{2})\s+Annual\s+Report',
        r'\bDecember\s+\d{1,2},?\s+(20\d{2})\b',
        r'\bJanuary\s+\d{1,2},?\s+(20\d{2})\b',
        r'\bJune\s+\d{1,2},?\s+(20\d{2})\b',
        r'\bSeptember\s+\d{1,2},?\s+(20\d{2})\b',
        r'\bMarch\s+\d{1,2},?\s+(20\d{2})\b'
    ]
    
    content_lower = content.lower()
    
    for pattern in fiscal_year_patterns:
        match = re.search(pattern, content_lower)
        if match:
            return match.group(1)
    
    
    sec_match = re.search(r'(\d{10})-(\d{2})-(\d{6})', filename)
    if sec_match:
        file_year = f"20{sec_match.group(2)}"  
        
        fiscal_year = str(int(file_year) - 1)
        return fiscal_year
    
     
    year_match = re.search(r'(20\d{2})', filename)
    if year_match:
        file_year = year_match.group(1)
        
        fiscal_year = str(int(file_year) - 1)
        return fiscal_year
    
   
    return "unknown_year"

def extract_mda_sections(input_dir, output_dir):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    count = 0
    
    for html_file in input_dir.glob("*.html"):
        try:
            with open(html_file, 'r', encoding='utf-8', errors='replace') as f:
                html_content = f.read()
            
            mdna_text = clean_text(extract_item_7_from_html(html_content))
            
            if "not found" not in mdna_text.lower() and len(mdna_text) > 500:
                
                print(f"Processing file: {html_file.name}")
                
             
                fiscal_year = extract_fiscal_year_from_content(mdna_text, html_file.name)
                print(f"Extracted fiscal year: {fiscal_year}")
                
                
                output_filename = f"MDNA_{fiscal_year}_{html_file.stem}.txt"
                output_path = output_dir / output_filename
                
                print(f"Output filename: {output_filename}")
                
                with open(output_path, 'w', encoding='utf-8') as out_file:
                    out_file.write(mdna_text)
                count += 1
                
        except Exception as e:
            print(f"Error processing {html_file.name}: {str(e)}")
    
    return count