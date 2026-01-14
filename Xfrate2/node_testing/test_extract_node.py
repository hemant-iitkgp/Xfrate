import os
import sys
import json
from Xfrate2.utils import logger
from Xfrate2.state import AgentState
from Xfrate2.nodes.extractor import extract_order

# Ensure we can import from the 'nodes' folder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'nodes')))

# Import the node function (Adjust 'nodes.extract_node' if your file is named differently)

def test_extract_node():
    logger.info(">>> TESTING NODE 2: extract_order (Azure OpenAI) <<<")
    
    # --- TEST DATA: A Sample Logistics Request ---
    sample_text = """
    Please book a Closed Body LCV truck for tomorrow.
    Pickup from: 123 Warehouse St, New Delhi.
    Destination: 456 Market Rd, Mumbai.
    The cargo is electronics, total weight about 1.5 tons.
    """
    
    # 1. Mock the Input State
    state: AgentState = {
        "file_path": "test_input.txt",
        "extracted_text": sample_text,
        "file_type": ".txt",  # Text mode test
        "raw_extraction": {},
        "validation_errors": [],
        "human_corrections": [],
        "final_orders": []
    }
    
    print(f"\n[Input Text]:\n{sample_text.strip()}\n")
    print("Sending to LLM... (This may take 5-10 seconds)")

    try:
        # 2. Run the Node
        result = extract_order(state)
        
        # 3. Validation Logic for the Test
        extraction = result.get("raw_extraction", {})
        orders = extraction.get("orders", [])
        
        if not orders:
            print("❌ FAILED: API returned no orders.")
            return

        first_order = orders[0]
        
        # Check specific fields to ensure 'Smart Extraction' happened
        veh_type = first_order.get("vehicle_type", {})
        weight = first_order.get("total_weight", {})
        date_info = first_order.get("pickup_date_and_time", {})

        print("\n✅ API CALL SUCCESSFUL!")
        print("-" * 40)
        print(f"Vehicle Detected: {veh_type.get('value')} (Conf: {veh_type.get('confidence')})")
        print(f"Weight Detected:  {weight.get('value')} (Conf: {weight.get('confidence')})")
        print(f"Date Interpreted: {date_info.get('value')} (Conf: {date_info.get('confidence')})")
        print("-" * 40)
        
        # 4. Strict Assertions
        assert veh_type.get('value') == "LCV", "Failed to extract Vehicle Type"
        assert weight.get('value') == 1.5, "Failed to extract Weight"
        assert weight.get('confidence') >= 0.8, "Confidence score is suspiciously low"
        
        print("\n>>> NODE 2 TEST PASSED <<<")
        print(orders)

    except Exception as e:
        print(f"\n❌ TEST FAILED with Error: {e}")

if __name__ == "__main__":
    test_extract_node()