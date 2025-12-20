import os
import json
import base64
import docx2txt
from enum import Enum
from pypdf import PdfReader
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv
from openai import AzureOpenAI
from dateutil import parser

# Load environment variables
load_dotenv()

# --- 1. Define Enums for Uniformity ---
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

class PackagingType(str, Enum):
    CARTON = "Carton Box"
    LOOSE = "Loose"
    DRUM = "Drum"
    GUNNY = "Gunny Bag"
    NOT_SPECIFIED = "Not specified"

class PODType(str, Enum):
    HARDCOPY = "Hardcopy"
    SOFTCOPY = "Softcopy"
    BOTH = "Both"

# --- 2. Define the Pydantic Schema ---
class FTLOrder(BaseModel):
    number_of_vehicle: int = Field(gt=0)
    vehicle_type: VehicleType
    vehicle_size: Optional[str] = None
    body_type: BodyType
    packaging_type: PackagingType
    pickup_address: str
    pickup_date_and_time: str
    destination_address: str
    expected_delivery_date_and_time: Optional[str] = None
    product_category: str
    product_description: str
    total_weight: float = Field(description="Weight in Metric Tons")
    shippers_note: Optional[str] = None
    pod_type: PODType

    # Validation logic to ensure Uniformity
    @field_validator("body_type", mode="before")
    @classmethod
    def normalize_body_type(cls, v: str) -> str:
        if not v: return BodyType.NOT_SPECIFIED
        v_clean = v.lower()
        if "open" in v_clean: return BodyType.OPEN
        if "close" in v_clean: return BodyType.CLOSED
        if "ref" in v_clean: return BodyType.REFRIGERATED
        return BodyType.NOT_SPECIFIED

    @field_validator("pod_type", mode="before")
    @classmethod
    def normalize_pod(cls, v: str) -> str:
        if not v: return PODType.BOTH
        v_clean = v.lower()
        if "hard" in v_clean: return PODType.HARDCOPY
        if "soft" in v_clean: return PODType.SOFTCOPY
        return PODType.BOTH
    @field_validator("pickup_date_and_time", mode="before")
    @classmethod
    def standardize_date(cls, v: str) -> str:
        if not v:
            return ""
        try:
            dt = parser.parse(v)
            return dt.strftime("%d-%m-%Y %H:%M")
        except Exception:
            return v

class FTLOrderResponse(BaseModel):
    orders: List[FTLOrder]

# --- 3. Initialize Azure Client ---
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2024-08-01-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

DEPLOYMENT_NAME = os.getenv("CHAT_COMPLETION_NAME")

# --- 4. Helper Functions ---
def extract_text_from_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".docx":
        return docx2txt.process(file_path)
    elif ext == ".pdf":
        reader = PdfReader(file_path)
        return " ".join([page.extract_text() for page in reader.pages])
    return None

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# --- 5. Main Processing Logic ---
def process_logistics_file(file_path):
    print(f"--- Processing: {file_path} ---")
    file_ext = os.path.splitext(file_path)[1].lower()
    
    system_msg = (
        "You are an expert logistics assistant. Extract all FTL order details. "
        "Strictly follow the allowed values for vehicle_type, body_type, and pod_type. "
        "If a specific value like 'Open body' is found, map it to the allowed Enum 'Open'."
    )

    messages = [{"role": "system", "content": system_msg}]

    if file_ext in [".jpg", ".jpeg", ".png"]:
        base64_image = encode_image(file_path)
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": "Extract all order details from this image."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]
        })
    else:
        text_content = extract_text_from_file(file_path)
        if not text_content:
            raise ValueError("Could not extract text from file.")
        messages.append({"role": "user", "content": text_content})

    completion = client.beta.chat.completions.parse(
        model=DEPLOYMENT_NAME,
        messages=messages,
        response_format=FTLOrderResponse,
        temperature=0.0
    )

    return completion.choices[0].message.parsed

# --- 6. Execution Loop ---
if __name__ == "__main__":
    os.makedirs("output_json", exist_ok=True)
    test_files = ["FileC.png"] 

    for file_name in test_files:
        if os.path.exists(file_name):
            try:
                result = process_logistics_file(file_name)
                output_path = f"output_json/{file_name}.json"
                with open(output_path, "w") as f:
                    # use result.model_dump() for Pydantic v2
                    json.dump(result.model_dump(), f, indent=4)
                
                print(f"Success! Uniform data saved to {output_path}")
            except Exception as e:
                print(f"Error processing {file_name}: {e}")
        else:
            print(f"File {file_name} not found.")