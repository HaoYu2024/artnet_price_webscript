# artnet_price_webscript
Code on 02/08/2025


# Art Auction Data Parser
A specialized Python script that extracts structured auction data from PDFs downloaded from Artnet's price database.

## Key Features
- Robust PDF text extraction using pdfplumber
- Intelligent pattern matching for auction metadata 
- Handles both 2D and 3D artwork dimensions
- Multi-currency price handling
- Error-resilient parsing with graceful fallbacks

## Core Components

### Auction Record Parsing
The script excels at extracting complex auction data fields:
```python
def parse_auction_data(text: str) -> List[Dict[str, Any]]:
    # Smart pattern matching for fields like:
    # - Artist name with numbered prefixes
    # - Artwork titles and descriptions
    # - Medium with fallback to description parsing
    # - Size in both imperial and metric units
    # - Sale information with lot numbers
    # - Price estimates and realized prices in multiple currencies
```

### Dimension Handling
Sophisticated size extraction supporting both 2D and 3D artworks:
```python
size_patterns = [
    # 3D works pattern 
    r'Size\s+Height\s+(\d+\.?\d*)\s*in\.?\s*;\s*Width\s+(\d+\.?\d*)\s*in\.?(?:\s*;\s*Depth\s+(\d+\.?\d*)\s*in\.?)?',
    # 2D works pattern
    r'Size\s+Height\s+(\d+\.?\d*)\s*in\.?\s*;\s*Width\s+(\d+\.?\d*)\s*in\.?'
]
```

### Price Processing
Advanced price extraction with multi-currency support:
```python
# Handles various price formats
estimate_pattern = r'Estimate\s*((?:\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+)\s*(?:-|to)\s*(?:\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+)\s*(?:USD|GBP|HKD|CNY|AUD|EUR|SGD))'
```

## Output
- Creates a standardized CSV with detailed auction records
- Includes comprehensive artwork details, sizing, and pricing information
- Handles missing data gracefully while maintaining data integrity

## Error Handling
- Robust error handling at multiple levels
- Detailed logging for debugging
- Continues processing despite individual record failures

