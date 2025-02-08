import os
import pandas as pd
import PyPDF2
import re
from typing import Optional, List, Dict, Any

#64+68+96+100+100+45+40+84

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract and preprocess text from PDF with improved entry separation."""
    text = ""
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            extracted_text = page.extract_text()
            if extracted_text:
                text += extracted_text + "\n"

    # First, normalize all whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Add entry separators before artist names and numbered entries
    artists = [
        "Avery Singer", "Harold Ancart", "Hernan Bas", "Jonas Wood",
        "Lisa Yuskavage", "Lucas Arruda", "Lucy Bull", "Scott Kahn"
    ]
    
    # Add separator before numbered artist entries
    for artist in artists:
        # Pattern matches both numbered and non-numbered artist entries
        pattern = f'(?:(?:\d+\s+)?{re.escape(artist)})'
        text = re.sub(pattern, f'\n@@@@{artist}', text)
    
    # Add markers for key fields (helps with parsing)
    field_markers = {
        'Title': '###TITLE###',
        'Description': '###DESC###',
        'Medium': '###MEDIUM###',
        'Year of Work': '###YEAR###',
        'Size': '###SIZE###',
        'Sale of': '###SALE###',
        'Estimate': '###EST###',
        'Sold For': '###SOLD###'
    }
    
    for field, marker in field_markers.items():
        text = text.replace(field, marker)
    
    # Clean up specific patterns
    text = text.replace('b.', 'born ')  # Normalize birth year format
    text = text.replace('[Lot', '\n[Lot')  # Ensure lot info starts on new line
    text = text.replace('USD Premium', 'USD')  # Normalize price format
    
    return text
def parse_auction_data(text: str) -> List[Dict[str, Any]]:
    """Parse auction data with improved size extraction."""
    if not isinstance(text, str) or not text.strip():
        return []
        
    auctions = []
    entries = text.split('@@@@')
    
    for entry in entries:
        if not entry.strip():
            continue
            
        try:
            # Print raw entry for debugging
            print("\n=== Raw Entry Start ===")
            print(entry[:500])
            print("=== Raw Entry End ===")
            
            # Basic fields extraction (same as before)
            artist_pattern = r'^(.*?)(?=###|$)'
            artist_match = re.search(artist_pattern, entry.strip())
            
            title_pattern = r'###TITLE###(.*?)(?=###|$)'
            title_match = re.search(title_pattern, entry, re.DOTALL)
            
            # Extract size with more lenient patterns
            size_patterns = [
                # Pattern 1: Standard format
                r'Size.*?Height\s*(\d+\.?\d*)\s*in\.?\s*;\s*Width\s*(\d+\.?\d*)\s*in\.?\s*/\s*Height\s*(\d+\.?\d*)\s*cm\.?\s*;\s*Width\s*(\d+\.?\d*)\s*cm',
                
                # Pattern 2: No units specified in pattern
                r'Height\s*(\d+\.?\d*)\s*[^0-9]*Width\s*(\d+\.?\d*)\s*[^0-9]*Height\s*(\d+\.?\d*)\s*[^0-9]*Width\s*(\d+\.?\d*)',
                
                # Pattern 3: More flexible spacing
                r'Size.*?H\w*\s*(\d+\.?\d*)\s*in\w*\s*[;,.]?\s*W\w*\s*(\d+\.?\d*)\s*in\w*\s*/?\s*H\w*\s*(\d+\.?\d*)\s*cm\w*\s*[;,.]?\s*W\w*\s*(\d+\.?\d*)\s*cm',
                
                # Pattern 4: Most lenient
                r'Height.*?(\d+\.?\d*)\s*in.*?Width.*?(\d+\.?\d*)\s*in.*?Height.*?(\d+\.?\d*)\s*cm.*?Width.*?(\d+\.?\d*)\s*cm'
            ]
            
            # Try each size pattern until one works
            size_match = None
            used_pattern = None
            for i, pattern in enumerate(size_patterns, 1):
                size_match = re.search(pattern, entry, re.DOTALL | re.IGNORECASE)
                if size_match:
                    used_pattern = f"Pattern {i}"
                    break
            
            # Print size debugging info
            print("\n=== Size Debug Info ===")
            print(f"Title: {title_match.group(1).strip() if title_match else 'Unknown'}")
            if size_match:
                print(f"Size found using {used_pattern}")
                print(f"Height (in): {size_match.group(1)}")
                print(f"Width (in): {size_match.group(2)}")
                print(f"Height (cm): {size_match.group(3)}")
                print(f"Width (cm): {size_match.group(4)}")
            else:
                print("No size match found")
                # Extract size section for analysis
                size_section = re.search(r'Size.*?(?=###|$)', entry, re.DOTALL)
                if size_section:
                    print("Raw size section:")
                    print(size_section.group(0))
            
            # Rest of the field extractions
            medium_pattern = r'###MEDIUM###(.*?)(?=###|$)'
            medium_match = re.search(medium_pattern, entry, re.DOTALL)
            
            year_patterns = [
                r'###YEAR###\s*(\d{4})',
                r'dated\s*[\'"]?(\d{4})',
                r'signed.*?dated.*?(\d{4})',
                r'(\d{4})\'?\s*(?:lower|upper)\s*(?:right|left)',
                r'created in\s*(\d{4})'
            ]
            year_match = None
            for pattern in year_patterns:
                year_match = re.search(pattern, entry, re.IGNORECASE)
                if year_match:
                    break
            
            sale_pattern = r'###SALE###(.*?):\s*([^[]+)\[Lot\s*(\d+[A-Z]?)\]'
            sale_match = re.search(sale_pattern, entry, re.DOTALL)
            
            estimate_pattern = r'###EST###\s*((?:\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+)\s*(?:-|to)\s*(?:\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+)\s*(?:USD|GBP|HKD|CNY)(?:\s*\(.*?\))?)'
            estimate_match = re.search(estimate_pattern, entry)
            
            sold_patterns = [
                r'###SOLD###\s*((?:\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+)\s*(?:USD|GBP|HKD|CNY)(?:\s*Premium)?)',
                r'###SOLD###\s*(Bought In)',
                r'###SOLD###\s*(Withdrawn)',
                r'###SOLD###\s*(Passed)',
                r'###SOLD###\s*(Not Sold)'
            ]
            sold_match = None
            for pattern in sold_patterns:
                sold_match = re.search(pattern, entry)
                if sold_match:
                    break

            def clean_text(match: Optional[re.Match], group: int = 1) -> str:
                if match and match.group(group):
                    return re.sub(r'\s+', ' ', match.group(group).strip())
                return ""
            
            auction_data = {
                "Artist": clean_text(artist_match),
                "Title": clean_text(title_match),
                "Medium": clean_text(medium_match),
                "Year": clean_text(year_match),
                "Height (in)": clean_text(size_match, 1) if size_match else "",
                "Width (in)": clean_text(size_match, 2) if size_match else "",
                "Height (cm)": clean_text(size_match, 3) if size_match else "",
                "Width (cm)": clean_text(size_match, 4) if size_match else "",
                "Auction House": clean_text(sale_match, 1) if sale_match else "",
                "Sale Date": clean_text(sale_match, 2) if sale_match else "",
                "Lot Number": clean_text(sale_match, 3) if sale_match else "",
                "Estimate Price": clean_text(estimate_match),
                "Sold Price": clean_text(sold_match)
            }
            
            if auction_data["Artist"] and auction_data["Title"].strip():
                auctions.append(auction_data)
                
        except Exception as e:
            print(f"Error parsing entry: {str(e)}")
            continue
            
    return auctions

def clean_text(match: Optional[re.Match], group: int = 1) -> str:
    """
    Clean matched text by removing excess whitespace.
    
    Args:
        match: Regex match object
        group: Group number to extract from match
        
    Returns:
        str: Cleaned text or empty string if no match
    """
    if match and match.group(group):
        return re.sub(r'\s+', ' ', match.group(group).strip())
    return ""



def process_folder(folder_path: str, output_csv: str) -> None:
    """
    Process all PDF files in a folder and combine results into a single CSV.
    
    Args:
        folder_path (str): Path to the folder containing PDF files
        output_csv (str): Path where the output CSV will be saved
        
    Raises:
        FileNotFoundError: If folder doesn't exist
        ValueError: If no PDF files found in folder
    """
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Folder not found: {folder_path}")
    
    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    if not pdf_files:
        raise ValueError(f"No PDF files found in {folder_path}")
    
    all_auctions = []
    for pdf_file in pdf_files:
        pdf_path = os.path.join(folder_path, pdf_file)
        try:
            text = extract_text_from_pdf(pdf_path)
            auctions = parse_auction_data(text)
            if auctions:
                all_auctions.extend(auctions)
                print(f"Successfully processed {pdf_file}")
            else:
                print(f"No auction data found in {pdf_file}")
        except Exception as e:
            print(f"Error processing {pdf_file}: {str(e)}")
    
    if not all_auctions:
        print("Warning: No auction data extracted from any files")
        
    df = pd.DataFrame(all_auctions) if all_auctions else pd.DataFrame()
    df.to_csv(output_csv, index=False)
    print(f"Data saved to {output_csv}")

def main(folder_path: str, output_csv: str) -> None:
    """Main function to process PDFs and generate CSV."""
    try:
        process_folder(folder_path, output_csv)
    except Exception as e:
        print(f"Error in main processing: {str(e)}")

if __name__ == "__main__":
    folder_path = r"C:\Users\haoyu\Downloads\auctionfiles"
    output_csv = r"C:\Users\haoyu\Downloads\auctionfiles\auction_data.csv"
    main(folder_path, output_csv)