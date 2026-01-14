# file: nodes/finalize_node.py
import json
import os
from datetime import datetime
from typing import List, Dict, Any
from Xfrate2.utils import logger
from Xfrate2.state import AgentState

# Configuration for "Databases"
SUCCESS_DB_PATH = "success_orders.json"
ERROR_DB_PATH = "needs_review_orders.json"

def finalize_and_route(state: AgentState) -> Dict[str, Any]:
    """
    Node 4: The Router & Formatter.
    Splits orders into 'Success' and 'Needs Review'.
    - Success: Flattened, formatted, and saved to success DB.
    - Needs Review: Raw data + Error details saved to error DB.
    """
    logger.info(">>> NODE 4: finalize_and_route STARTED <<<")
    
    raw_extraction = state.get("raw_extraction", {})
    orders = raw_extraction.get("orders", [])
    validation_errors = state.get("validation_errors", [])
    
    success_batch = []
    error_batch = []

    # 1. Map Errors to specific Order Indices for quick lookup
    # Structure: { 0: [Error1, Error2], 1: [] }
    error_map = {i: [] for i in range(len(orders))}
    for err in validation_errors:
        idx = err.get("order_index")
        if idx is not None and idx in error_map:
            error_map[idx].append(err)

    # 2. Iterate and Route
    for index, order in enumerate(orders):
        order_errors = error_map[index]
        
        if not order_errors:
            # --- PATH A: SUCCESS ---
            # No errors found. Format and Flatten.
            clean_order = _flatten_and_format(order)
            success_batch.append(clean_order)
        else:
            # --- PATH B: NEEDS REVIEW ---
            # Has errors. Bundle raw data with the specific errors.
            error_record = {
                "order_metadata": {"index_in_file": index, "source_file": state.get("file_path")},
                "raw_data": order, # Keep full context (confidence etc) for the human
                "issues": order_errors
            }
            error_batch.append(error_record)

    # 3. "Database" Operations (Appending to JSON files)
    if success_batch:
        _append_to_json_file(SUCCESS_DB_PATH, success_batch)
        logger.info(f"Committed {len(success_batch)} orders to Success DB.")

    if error_batch:
        _append_to_json_file(ERROR_DB_PATH, error_batch)
        logger.warning(f"Sent {len(error_batch)} orders to Review Queue.")

    # 4. Update State (Optional, but good for tracing)
    return {
        "final_orders": success_batch
    }

# --- HELPER FUNCTIONS ---

def _flatten_and_format(order: Dict) -> Dict:
    """
    Converts the complex 'FieldWithConfidence' structure into 
    the flat, strict format required by output.json.
    Also handles Date conversion (YYYY-MM-DD -> dd/mm/yyyy).
    """
    flat = {}
    
    for key, field_data in order.items():
        if not isinstance(field_data, dict):
            continue
            
        value = field_data.get("value")
        
        # Date Formatting Rule (ISO to Database Req)
        if "date" in key and isinstance(value, str):
            try:
                # Assuming input is ISO YYYY-MM-DD HH:MM (from our Validator/Cleaner)
                # Convert to "dd/mm/yyyy hour:minute"
                dt = datetime.strptime(value, "%Y-%m-%d %H:%M")
                value = dt.strftime("%d/%m/%Y %H:%M")
            except ValueError:
                pass # If format fails, keep original string

        flat[key] = value
        
    return flat

def _append_to_json_file(filepath: str, new_records: List[Dict]):
    """Simulates appending to a NoSQL database."""
    data = []
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            pass # Start fresh if file is corrupted
            
    data.extend(new_records)
    
    with open(filepath, "w") as f:
        json.dump(data, f, indent=4)