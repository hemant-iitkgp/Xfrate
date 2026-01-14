import os
import sys
import json
from Xfrate2.utils import logger
from Xfrate2.state import AgentState
from Xfrate2.nodes.finalize_node import finalize_and_route, SUCCESS_DB_PATH, ERROR_DB_PATH


def test_finalize_node():
    logger.info(">>> TESTING NODE 4: finalize_and_route <<<")
    
    # Clean up old DB files for clean test
    if os.path.exists(SUCCESS_DB_PATH): os.remove(SUCCESS_DB_PATH)
    if os.path.exists(ERROR_DB_PATH): os.remove(ERROR_DB_PATH)

    # --- MOCK STATE ---
    # Order 0: Perfect (Should go to Success DB)
    # Order 1: Has Error (Should go to Error DB)
    state: AgentState = {
        "file_path": "test_batch_001.pdf",
        "raw_extraction": {
            "orders": [
                # Order 0
                {
                    "vehicle_type": {"value": "LCV", "confidence": 0.9},
                    "pickup_date_and_time": {"value": "2026-01-05 14:30", "confidence": 1.0},
                    "total_weight": {"value": 100, "confidence": 0.9}
                },
                # Order 1
                {
                    "vehicle_type": {"value": "Unknown", "confidence": 0.2}, # Low confidence
                    "pickup_date_and_time": {"value": None, "confidence": 0.0}, # Missing
                }
            ]
        },
        # Validation Errors pointing only to Order 1
        "validation_errors": [
            {"order_index": 1, "field": "vehicle_type", "issue": "Low Confidence"},
            {"order_index": 1, "field": "pickup_date_and_time", "issue": "Missing Value"}
        ]
    }

    # --- RUN NODE ---
    finalize_and_route(state)

    # --- VERIFY SUCCESS DB ---
    if os.path.exists(SUCCESS_DB_PATH):
        with open(SUCCESS_DB_PATH, 'r') as f:
            success_data = json.load(f)
        print(f"\n[Success DB] Contains {len(success_data)} records.")
        
        # Check Date Formatting
        date_val = success_data[0].get("pickup_date_and_time")
        if date_val == "05/01/2026 14:30":
            print("✅ Date Formatting Logic (dd/mm/yyyy) Worked!")
        else:
            print(f"❌ Date Formatting Failed. Got: {date_val}")
    else:
        print("❌ Success DB file not created.")

    # --- VERIFY ERROR DB ---
    if os.path.exists(ERROR_DB_PATH):
        with open(ERROR_DB_PATH, 'r') as f:
            error_data = json.load(f)
        print(f"[Error DB] Contains {len(error_data)} records.")
        
        # Check Bundling
        if len(error_data[0]["issues"]) == 2:
            print("✅ Error Bundling Worked (Raw Data + 2 Issues preserved).")
        else:
            print("❌ Error Bundling Failed.")
    else:
        print("❌ Error DB file not created.")

    print("\n>>> NODE 4 TEST COMPLETE <<<")

if __name__ == "__main__":
    test_finalize_node()