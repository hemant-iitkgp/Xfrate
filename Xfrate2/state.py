from typing import TypedDict, List, Dict, Any, Optional, TypeVar, Generic
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from dateutil import parser

# Define a Type Variable for Generics
T = TypeVar('T')

# --- SECTION 1: ENUMS ---
class VehicleType(str, Enum):
    LCV = "LCV"
    HCV = "HCV"
    TRAILER = "Trailer"
    CITY_LOGISTIC = "City Logistic"
    NOT_SPECIFIED = "Not specified"

class BodyType(str, Enum):
    OPEN = "Open"
    CLOSED = "Closed"
    REFRIGERATED = "Refrigerated"
    NOT_SPECIFIED = "Not specified"

class PODType(str, Enum):
    HARDCOPY = "Hardcopy"
    SOFTCOPY = "Softcopy"
    BOTH = "Both"


# --- SECTION 2: PYDANTIC MODELS (Now with Generics) ---

# 1. The Generic Wrapper
class FieldWithConfidence(BaseModel, Generic[T]):
    """
    A generic wrapper. 
    Usage: FieldWithConfidence[float] enforces that 'value' MUST be a float.
    """
    value: Optional[T] = Field(description="The extracted value")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    reasoning: Optional[str] = Field(description="Why this value was chosen")

# 2. The Strict Schema
class FTLOrder(BaseModel):
    # Notice the square brackets [Type]. This forces strict validation.
    
    # Enum Fields (Strictly limits output to Allowed Values)
    vehicle_type: FieldWithConfidence[VehicleType] 
    body_type: FieldWithConfidence[BodyType]
    pod_type: Optional[FieldWithConfidence[PODType]] = None

    # Numeric Fields
    number_of_vehicle: FieldWithConfidence[int]
    total_weight: FieldWithConfidence[float]

    # String Fields
    pickup_address: FieldWithConfidence[str]
    destination_address: FieldWithConfidence[str]
    product_category: FieldWithConfidence[str]
    product_description: FieldWithConfidence[str]
    
    # Date Fields (String for now, cleaned by validator)
    pickup_date_and_time: FieldWithConfidence[str]
    expected_delivery_date_and_time: Optional[FieldWithConfidence[str]] = None
    
    # Other
    vehicle_size: Optional[FieldWithConfidence[str]] = None
    shippers_note: Optional[FieldWithConfidence[str]] = None


    # --- THE CLEANERS (Validators) ---
    # These work exactly the same as before.
    
    @field_validator('pickup_date_and_time', 'expected_delivery_date_and_time', mode='before')
    @classmethod
    def clean_dates(cls, v):
        if isinstance(v, dict) and v.get('value'):
            try:
                dt = parser.parse(str(v['value']))
                v['value'] = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass 
        return v

    @field_validator('vehicle_type', 'body_type', 'pod_type', mode='before')
    @classmethod
    def clean_enums(cls, v):
        """
        Maps fuzzy terms. Pydantic will run this BEFORE checking the Generic Type.
        """
        if isinstance(v, dict) and v.get('value') and isinstance(v['value'], str):
            val_lower = v['value'].lower()
            
            # Example: Map 'Open truck' to BodyType.OPEN enum value
            if 'open' in val_lower: v['value'] = BodyType.OPEN.value
            elif 'close' in val_lower: v['value'] = BodyType.CLOSED.value
            elif 'ref' in val_lower: v['value'] = BodyType.REFRIGERATED.value
            
            # If the LLM output 'LCV Truck', map it to 'LCV'
            if 'lcv' in val_lower: v['value'] = VehicleType.LCV.value
            elif 'hcv' in val_lower: v['value'] = VehicleType.HCV.value
            
        return v

class FTLOrderResponse(BaseModel):
    orders: List[FTLOrder]

# --- SECTION 3: LANGGRAPH STATE ---
# (Stays the same as previous response)
from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):
    """
    State representing the full lifecycle of the extraction process.
    """
    # --- 1. Inputs ---
    file_path: str
    
    # --- 2. Processing Data ---
    extracted_text: str
    file_type: str

    # --- 3. The Master Record (Mutable) ---
    # Stores {"orders": [ { "vehicle_type": { "value": "...", "confidence": ... } } ] }
    raw_extraction: Dict[str, Any] 

    # --- 4. The Loop Drivers ---
    
    # A. The Problem List
    # Populated by Node C (Validator). Cleared if validation passes.
    # Format: [{'order_index': int, 'field': str, 'issue': str, 'current_value': Any}]
    validation_errors: List[Dict[str, Any]]

    # B. The Human Input Inbox
    # Populated by the User (during Interrupt). Processed & Cleared by Node D (Human Node).
    # Format: [{'order_index': int, 'field': str, 'corrected_value': Any}]
    human_corrections: List[Dict[str, Any]]

    # --- 5. Final Output ---
    final_orders: List[Dict[str, Any]]