# file: extract_node.py
import os
import json
from openai import AzureOpenAI
from openai import APITimeoutError, APIError, RateLimitError, AuthenticationError
from pydantic import ValidationError
from typing import Dict, Any
from pathlib import Path

# Internal imports
from Xfrate2.utils import logger
from Xfrate2.state import AgentState, FTLOrderResponse
from Xfrate2.nodes.prompt import EXTRACT_ORDER_SYSTEM_PROMPT

from dotenv import load_dotenv
# env_path=Xfrate2.env
load_dotenv()

# --- PATH CONFIGURATION ---
# 1. Get the directory of THIS file (Xfrate2/nodes)
current_file_dir = Path(__file__).resolve().parent

# 2. Point to the .env file in the parent directory (Xfrate2/.env)
#    We go up one level (.parent) to get out of 'nodes' into 'Xfrate2'
env_path = current_file_dir.parent / '.env'

# 3. Load the .env file if it exists
# load_dotenv(dotenv_path=env_path)


# --- CONFIGURATION ---
# Ensure you have these set in your environment variables or .env file
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2024-08-01-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    max_retries=2,
    timeout=60.0
)
DEPLOYMENT_NAME = os.getenv("CHAT_COMPLETION_NAME", "gpt-4o") 

def extract_order(state: AgentState) -> Dict[str, Any]:
    """
    Node 2: The Intelligence Layer.
    Extracts structured order data using Azure OpenAI.
    Handles Text and Images (Vision) with a self-correction loop.
    """
    logger.info(">>> NODE 2: extract_order STARTED <<<")
    
    extracted_text = state.get("extracted_text", "")
    file_type = state.get("file_type", "").lower()
    
    # 1. Determine Input Mode (Text vs Vision)
    is_image = file_type in [".png", ".jpg", ".jpeg", ".bmp"]
    
    messages = [
        {"role": "system", "content": EXTRACT_ORDER_SYSTEM_PROMPT}
    ]

    if is_image:
        logger.info(f"Detected Image ({file_type}). Preparing Vision Payload...")
        # For Vision, 'extracted_text' contains the Base64 string from Node 1
        user_content = [
            {"type": "text", "text": "Extract the Logistics Order details from this image."},
            {
                "type": "image_url", 
                "image_url": {"url": f"data:image/jpeg;base64,{extracted_text}"}
            }
        ]
        messages.append({"role": "user", "content": user_content})
    else:
        logger.info(f"Detected Text ({file_type}). Preparing Text Payload...")
        user_content = f"Extract the Logistics Order details from the following text:\n\n{extracted_text}"
        messages.append({"role": "user", "content": user_content})

    # 2. The Agentic Retry Loop (Layer 2 Defense)
    MAX_RETRIES = 3
    current_try = 0
    
    while current_try < MAX_RETRIES:
        try:
            current_try += 1
            logger.info(f"LLM Call Attempt {current_try}/{MAX_RETRIES}...")

            # API Call with Structured Outputs
            completion = client.beta.chat.completions.parse(
                model=DEPLOYMENT_NAME,
                messages=messages,
                response_format=FTLOrderResponse, 
                temperature=0.0, # Deterministic for extraction
            )

            # 3. Parse and Validation
            # If this succeeds, Pydantic has validated the structure
            parsed_response = completion.choices[0].message.parsed
            
            # Convert to clean Dictionary for State Storage
            raw_dict = parsed_response.model_dump(mode='json')
            
            logger.info(f"[SUCCESS]Extraction Successful on attempt {current_try}; {len(raw_dict["orders"])} orders extracted")
            return {"raw_extraction": raw_dict}

        except ValidationError as e:
            logger.warning(f"⚠️ Validation Error on Attempt {current_try}: {e}")
            
            # Self-Correction: Add the error to conversation history so LLM can fix it
            # We must convert the previous assistant output to string content for context
            bad_response = completion.choices[0].message.content
            messages.append({"role": "assistant", "content": bad_response})
            messages.append({
                "role": "user", 
                "content": f"Your response failed validation. Error: {str(e)}. Please fix the format and try again."
            })

        except APITimeoutError as e:
            logger.error("API Timeout: Azure OpenAI did not respond in time.")
            continue

        except RateLimitError:
            logger.error("Rate limit exceeded from Azure OpenAI.")
            break

        except AuthenticationError:
            logger.error("Authentication failed: Check Azure OpenAI credentials.")
            break

        except APIError as e:
            logger.error(f"Azure OpenAI API error: {str(e)}")
            break

        except Exception as e:
            logger.error(f"Unexpected system error: {e}", exc_info=True)
            # logger.error(f"Critical API Error")
            # Check if it's an Auth error or Rate Limit (Logic to break loop can be added here)
            break

    # 4. Fallback (If all retries fail)
    logger.error("Max retries reached. Returning empty order to trigger Human Loop.")
    
    # We return an 'empty' order structure. 
    # The Validation Node will see 'value: None' and flag it for the user.
    empty_structure = {
        "orders": [] 
    }
    return {"raw_extraction": empty_structure}