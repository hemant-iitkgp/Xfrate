import os
import sys
import json
from Xfrate2.utils import logger
from Xfrate2.state import AgentState
from Xfrate2.nodes.validate_node import validate_data

# Ensure we can import from the 'nodes' folder
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'nodes')))

def test_validate_node():
    logger.info(">>> TESTING NODE 3: validate_data <<<")
    
    # --- SCENARIO 1: THE HAPPY PATH (Perfect Data) ---
    # Everything is present, high confidence, and logical.
    good_order = {
        "orders": [{
            "vehicle_type": {"value": "LCV", "confidence": 0.95},
            "pickup_address": {"value": "123 Main St", "confidence": 1.0},
            "destination_address": {"value": "456 Market Rd", "confidence": 1.0},
            "pickup_date_and_time": {"value": "2026-01-01 10:00", "confidence": 1.0},
            "total_weight": {"value": 2.5, "confidence": 0.9},
            "number_of_vehicle": {"value": 1, "confidence": 0.9}
        }]
    }
    
    # --- SCENARIO 2: THE DIRTY DATA (Fails All Checks) ---
    bad_order = {
        "orders": [{
            # 1. Missing Data (Layer 1 Error)
            "vehicle_type": {"value": None, "confidence": 0.0}, 
            
            # 2. Low Confidence (Layer 2 Error)
            "pickup_address": {"value": "Some warehouse?", "confidence": 0.4},
            
            # 3. Physics Fail (Layer 3 Error)
            "total_weight": {"value": -100.0, "confidence": 0.9},
            "number_of_vehicle": {"value": 0, "confidence": 0.9},

            # Just to satisfy required keys so we don't get 'missing' error for these
            "destination_address": {"value": "Valid", "confidence": 1.0},
            "pickup_date_and_time": {"value": "2026-01-01", "confidence": 1.0}
        }]
    }

    # --- RUN TEST 1: EXPECT SUCCESS ---
    print("\n[Test 1] Clean Data Input...")
    state_clean: AgentState = {"raw_extraction": good_order}
    result_clean = validate_data(state_clean)
    errors_clean = result_clean["validation_errors"]
    print(errors_clean)
    
    if len(errors_clean) == 0:
        print("✅ Test 1 Passed: No errors found.")
    else:
        print(f"❌ Test 1 Failed: Found unexpected errors: {errors_clean}")

    # --- RUN TEST 2: EXPECT FAILURES ---
    print("\n[Test 2] Dirty Data Input (Expecting 4 errors)...")
    state_dirty: AgentState = {"raw_extraction": bad_order}
    result_dirty = validate_data(state_dirty)
    errors_dirty = result_dirty["validation_errors"]
    print(errors_dirty)

    # Analyze Errors
    error_types = [e['issue'] for e in errors_dirty]
    fields_flagged = [e['field'] for e in errors_dirty]
    
    print(f"Found {len(errors_dirty)} errors: {error_types}")
    
    # Assertions
    failed = False
    if "vehicle_type" not in fields_flagged: 
        print("❌ Failed to catch Missing Value")
        failed = True
    if "pickup_address" not in fields_flagged: 
        print("❌ Failed to catch Low Confidence")
        failed = True
    if "total_weight" not in fields_flagged: 
        print("❌ Failed to catch Negative Weight")
        failed = True
        
    if not failed:
        print("✅ Test 2 Passed: All 3 layers caught errors correctly.")

    print("\n>>> NODE 3 TEST COMPLETE <<<")

if __name__ == "__main__":
    test_validate_node()