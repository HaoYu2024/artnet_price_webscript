import os
import pandas as pd
import PyPDF2
import re
from typing import Optional, List, Dict, Any

#64+68+96+100+100+45+40+84

import pdfplumber  # Changed from PyPDF2 to pdfplumber


def parse_auction_data(text: str) -> List[Dict[str, Any]]:
    """Parse auction data from raw PDF text format."""
    if not isinstance(text, str) or not text.strip():
        return []
        
    auctions = []
    # Split by numbered entries (e.g., "1 Artist Name", "2 Artist Name")
    entries = re.split(r'\n(?=\d+\s+[A-Za-z\s]+\n)', text)
    
    for entry in entries:
        if not entry.strip():
            continue
            
        try:
            auction_data = {}
            
            # Artist extraction - now matches the number prefix format
            artist_pattern = r'^\d+\s+([A-Za-z\s]+)'
            artist_match = re.search(artist_pattern, entry.strip())
            if artist_match:
                auction_data["Artist"] = clean_text(artist_match)
            
            # Title extraction - matches after "Title" label
            title_pattern = r'Title\s+(.*?)(?=\n|Description|$)'
            title_match = re.search(title_pattern, entry, re.DOTALL)
            auction_data["Title"] = clean_text(title_match)
            
            # Medium extraction
            medium_pattern = r'Medium\s+(.*?)(?=\n|$)'
            medium_match = re.search(medium_pattern, entry, re.DOTALL)
            auction_data["Medium"] = clean_text(medium_match)
            
            # Year extraction
            year_patterns = [
                r'Year of Work\s*(\d{4})',
                r'dated\s*[\'"]?(\d{4})',
                r'signed.*?dated.*?(\d{4})',
                r'created in\s*(\d{4})'
            ]
            for pattern in year_patterns:
                year_match = re.search(pattern, entry, re.IGNORECASE)
                if year_match:
                    auction_data["Year"] = clean_text(year_match)
                    break
            
            # Size extraction
            size_pattern = r'Size\s+Height\s+(\d+\.?\d*)\s*in\.?\s*;\s*Width\s+(\d+\.?\d*)\s*in\.?\s*/\s*Height\s+(\d+\.?\d*)\s*cm\.?\s*;\s*Width\s+(\d+\.?\d*)\s*cm'
            size_match = re.search(size_pattern, entry, re.DOTALL | re.IGNORECASE)
            if size_match:
                auction_data["Height (in)"] = clean_text(size_match, 1)
                auction_data["Width (in)"] = clean_text(size_match, 2)
                auction_data["Height (cm)"] = clean_text(size_match, 3)
                auction_data["Width (cm)"] = clean_text(size_match, 4)
            
            # Sale information
            sale_pattern = r'Sale of\s+(.*?)(?:\[Lot\s*(\d+[A-Z]?)\])'
            sale_match = re.search(sale_pattern, entry, re.DOTALL)
            if sale_match:
                sale_text = clean_text(sale_match, 1)
                # Split auction house and date if possible
                parts = sale_text.split(':', 1)
                if len(parts) > 1:
                    auction_data["Auction House"] = parts[0].strip()
                    auction_data["Sale Date"] = parts[1].strip()
                else:
                    auction_data["Auction House"] = sale_text
                auction_data["Lot Number"] = clean_text(sale_match, 2) if sale_match.group(2) else ""
            
            # Estimate with improved currency handling
            estimate_pattern = r'Estimate\s*((?:\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+)\s*(?:-|to)\s*(?:\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+)\s*(?:USD|GBP|HKD|CNY|AUD|EUR|SGD)(?:\s*\(.*?\))?)'
            estimate_match = re.search(estimate_pattern, entry)
            auction_data["Estimate Price"] = clean_text(estimate_match) if estimate_match else ""
            
            # Sold price with improved handling
            sold_price_pattern = r'Sold For\s*((?:[\d,]+\s*[A-Z]{3})|(?:Bought In)|(?:Withdrawn)|(?:Passed)|(?:Not Sold))(?:\s*(?:Premium|Hammer))?(?:\s*\(([\d,]+\s*USD)\))?'
            sold_match = re.search(sold_price_pattern, entry)
            if sold_match:
                price = clean_text(sold_match, 1)
                usd_price = clean_text(sold_match, 2) if sold_match.group(2) else ""
                auction_data["Sold Price"] = f"{price} ({usd_price})" if usd_price else price
            
            # Only add entry if we have at least an artist or title
            if auction_data.get("Artist") or auction_data.get("Title"):
                auctions.append(auction_data)
                
        except Exception as e:
            print(f"Error parsing entry: {str(e)}")
            print(f"Problematic entry: {entry[:200]}...")  # Print first 200 chars of problematic entry
            continue
            
    return auctions

def clean_text(match: Optional[re.Match], group: int = 1) -> str:
    """Clean matched text by removing excess whitespace."""
    if match and match.group(group):
        return re.sub(r'\s+', ' ', match.group(group).strip())
    return ""

def process_folder(folder_path: str, output_csv: str) -> None:
    """Process all PDF files in a folder and combine results into a single CSV."""
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Folder not found: {folder_path}")
    
    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    if not pdf_files:
        raise ValueError(f"No PDF files found in {folder_path}")
    
    all_auctions = []
    for pdf_file in pdf_files:
        pdf_path = os.path.join(folder_path, pdf_file)
        try:
            print(f"\nProcessing {pdf_file}...")
            
            # Read PDF with pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        extracted_text = page.extract_text()
                        if extracted_text:
                            text += extracted_text + "\n"
                    except Exception as e:
                        print(f"Error extracting text from page {page_num}: {str(e)}")
            
            # Print sample of extracted text for debugging
            print(f"Sample of extracted text:\n{text[:500]}...\n")
            
            auctions = parse_auction_data(text)
            if auctions:
                all_auctions.extend(auctions)
                print(f"Successfully extracted {len(auctions)} records from {pdf_file}")
            else:
                print(f"No auction data found in {pdf_file}")
        except Exception as e:
            print(f"Error processing {pdf_file}: {str(e)}")
    
    if not all_auctions:
        print("Warning: No auction data extracted from any files")
        return
        
    df = pd.DataFrame(all_auctions)
    df.to_csv(output_csv, index=False)
    print(f"\nData saved to {output_csv}")
    print(f"Total records extracted: {len(all_auctions)}")

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract and preprocess text from PDF with improved encoding support."""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            extracted_text = page.extract_text()
            if extracted_text:
                text += extracted_text + "\n"

    # Normalize all whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Add entry separators with more precise matching
    artists = [
        "Avery Singer", "Harold Ancart", "Hernan Bas", "Jonas Wood",
        "Lisa Yuskavage", "Lucas Arruda", "Lucy Bull", "Scott Kahn"
    ]
    
    # Improved artist pattern to avoid mid-entry splits
    artist_pattern = r'(?<=\n)(?:\d+\s+)?(?:' + '|'.join(re.escape(artist) for artist in artists) + r')\b'
    text = re.sub(artist_pattern, lambda m: f'\n@@@@{m.group().lstrip()}', text)
    
    # Field markers with context-aware replacement
    field_markers = {
        r'Title\s*:?\s*': '###TITLE###',
        r'Description\s*:?\s*': '###DESC###',
        r'Medium\s*:?\s*': '###MEDIUM###',
        r'Year of Work\s*:?\s*': '###YEAR###',
        r'Size\s*:?\s*': '###SIZE###',
        r'Sale of\s*:?\s*': '###SALE###',
        r'Estimate\s*:?\s*': '###EST###',
        r'Sold For\s*:?\s*': '###SOLD###'
    }
    
    # Replace fields only when they appear as section headers
    for pattern, marker in field_markers.items():
        text = re.sub(
            rf'\n({pattern})', 
            f'\n{marker}', 
            text, 
            flags=re.IGNORECASE
        )
    
    # Cleanup patterns
    replacements = {
        r'\b(b\.)\s*(\d{4})': r'born \2',  # Birth year formatting
        r'\[Lot': '\n[Lot',                # Ensure lot info on new line
        r'USD Premium': 'USD'               # Normalize price format
    }
    
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)
    
    return text





  

def main(folder_path: str, output_csv: str) -> None:
    """Main function to process PDFs and generate CSV."""
    try:
        process_folder(folder_path, output_csv)
    except Exception as e:
        print(f"Error in main processing: {str(e)}")

if __name__ == "__main__":
    folder_path = r"C:\Users\haoyu\Downloads\auctionfiles"
    output_csv = r"C:\Users\haoyu\Downloads\auctionfiles\auction_data2.csv"
    main(folder_path, output_csv)