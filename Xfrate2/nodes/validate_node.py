# file: nodes/validate_node.py
from typing import List, Dict, Any
from Xfrate2.utils import logger
from Xfrate2.state import AgentState

# --- CONFIGURATION ---
CONFIDENCE_THRESHOLD = 0.8
REQUIRED_FIELDS = [
    "vehicle_type", 
    "pickup_address", 
    "pickup_date_and_time", 
    "total_weight",
    "destination_address"
]

def validate_data(state: AgentState) -> Dict[str, Any]:
    """
    Node 3: The Guardrails.
    Runs a 3-layer validation pipeline on every extracted order.
    1. Completeness Check (Is data missing?)
    2. Confidence Check (Is the AI guessing?)
    3. Physics Check (Is the data logical?)
    """
    logger.info(">>> NODE 3: validate_data STARTED <<<")
    
    raw_extraction = state.get("raw_extraction", {})
    orders = raw_extraction.get("orders", [])
    
    # The master list of all errors found across all orders
    all_validation_errors = []

    if not orders:
        logger.warning("Critical: No orders found in extraction.")
        return {
            "validation_errors": [{
                "order_index": 0,
                "field": "general",
                "issue": "No orders found in file",
                "current_value": None
            }]
        }

    # --- MAIN LOOP: Process One Order at a Time ---
    for index, order in enumerate(orders):
        # Layer 1: Check for Missing Data
        errs_1 = _check_completeness(order, index)
        
        # Layer 2: Check for Low Confidence
        errs_2 = _check_confidence(order, index)
        
        # Layer 3: Check Business Physics (Negative weights, etc.)
        errs_3 = _check_physics(order, index)
        
        # Aggregate logic: We show ALL errors to the user at once
        all_validation_errors.extend(errs_1 + errs_2 + errs_3)

    # Log Summary
    if all_validation_errors:
        logger.warning(f"Validation finished with {len(all_validation_errors)} issues.")
    else:
        logger.info("Validation passed. Data is clean.")

    # Update State
    return {"validation_errors": all_validation_errors}


# --- SUB-NODES (The Modular Logic Layers) ---

def _check_completeness(order: Dict, index: int) -> List[Dict]:
    """Layer 1: Ensures all mandatory fields are present."""
    errors = []
    
    for field in REQUIRED_FIELDS:
        field_data = order.get(field)
        
        # Scenario A: Field is missing entirely from JSON
        if field_data is None:
            errors.append({
                "order_index": index,
                "field": field,
                "issue": "Field is missing",
                "current_value": None
            })
            continue

        # Scenario B: Field exists but value is explicit None/Null
        # (This happens when LLM obeys 'return null if not found')
        val = field_data.get("value")
        if val is None:
            errors.append({
                "order_index": index,
                "field": field,
                "issue": "Missing required value",
                "current_value": None
            })
            
    return errors


def _check_confidence(order: Dict, index: int) -> List[Dict]:
    """Layer 2: Flags values where the AI is uncertain."""
    errors = []
    
    for field_name, field_data in order.items():
        # Skip metadata or non-dict fields
        if not isinstance(field_data, dict):
            continue
            
        value = field_data.get("value")
        confidence = field_data.get("confidence", 0.0)
        
        # Only check confidence if we actually have a value
        if value is not None:
            if confidence < CONFIDENCE_THRESHOLD:
                errors.append({
                    "order_index": index,
                    "field": field_name,
                    "issue": f"Low Confidence ({confidence:.2f})",
                    "current_value": value
                })
                
    return errors


def _check_physics(order: Dict, index: int) -> List[Dict]:
    """Layer 3: Basic logic checks (Phase 1 Physics)."""
    errors = []
    
    # Check 1: Weight must be positive
    weight_data = order.get("total_weight", {})
    if weight_data and weight_data.get("value"):
        try:
            val = float(weight_data["value"])
            if val <= 0:
                errors.append({
                    "order_index": index,
                    "field": "total_weight",
                    "issue": "Weight must be positive",
                    "current_value": val
                })
        except (ValueError, TypeError):
            pass # Pydantic usually catches types, but safety first

    # Check 2: Vehicle Count must be at least 1
    count_data = order.get("number_of_vehicle", {})
    if count_data and count_data.get("value"):
        if count_data["value"] < 1:
            errors.append({
                "order_index": index,
                "field": "number_of_vehicle",
                "issue": "Vehicle count must be at least 1",
                "current_value": count_data["value"]
            })
            
    return errors