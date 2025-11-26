from pydantic import BaseModel, Field
from typing import Optional, List

class Invoice(BaseModel):
    """Represents a simple invoice."""
    invoice_id: Optional[str] = Field(None, description="The invoice number.")
    vendor_name: Optional[str] = Field(None, description="The name of the vendor.")
    invoice_date: Optional[str] = Field(None, description="The date of the invoice.")
    total_amount: Optional[float] = Field(None, description="The total amount of the invoice.")

class ExtractionRequest(BaseModel):
    """Request model for data extraction."""
    input_text: str = Field(..., description="The user's query text.")
    uploaded_file_name: str = Field(..., description="The name of the uploaded file.")
