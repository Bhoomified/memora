import io
import pdfplumber
from PIL import Image
import pytesseract

def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """
    Extracts raw text content from uploaded PDFs or Images (PNG/JPG).
    """
    text = ""
    filename_lower = filename.lower()
    
    try:
        if filename_lower.endswith(".pdf"):
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
                        
        elif filename_lower.endswith((".png", ".jpg", ".jpeg")):
            image = Image.open(io.BytesIO(file_bytes))
            text = pytesseract.image_to_string(image)
            
    except Exception as e:
        print(f"Error parsing file {filename}: {str(e)}")
        
    return text.strip()