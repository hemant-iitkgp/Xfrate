import os
import shutil
from Xfrate2.state import AgentState
from Xfrate2.nodes.file_reader import parse_document
from Xfrate2.utils import logger

# --- HELPER: Create Dummy Files for Testing ---
def setup_dummy_files():
    """Creates temporary files to test the parser logic."""
    # 1. Text File
    with open("test_invoice.txt", "w") as f:
        f.write("Order: 10 LCV Trucks\nPickup: Delhi\nDate: Tomorrow")
    
    # 2. Dummy PDF (Empty file with pdf extension just to test routing, 
    # note: real extraction needs a real PDF, but this tests the path)
    with open("test_empty.pdf", "wb") as f:
        f.write(b"%PDF-1.4...") 

def cleanup_dummy_files():
    """Removes the temp files."""
    for f in ["test_invoice.txt", "test_empty.pdf"]:
        if os.path.exists(f):
            os.remove(f)

# --- TEST 1: Parse Document Node ---
def test_parse_node():
    logger.info(">>> TESTING NODE 1: parse_document <<<")
    setup_dummy_files()
    
    # Scenario A: Valid Text File
    try:
        # 1. Mock the Input State
        initial_state: AgentState = {
            "file_path": "test_invoice.txt",
            "extracted_text": "",
            "file_type": "",
            "raw_extraction": {},
            "validation_errors": [],
            "human_corrections": [],
            "final_orders": []
        }
        
        # 2. Run the Node
        print(f"\n[Test A] Input: {initial_state['file_path']}")
        result = parse_document(initial_state)
        
        # 3. Assertions (Check if it worked)
        assert "extracted_text" in result
        assert "file_type" in result
        assert "10 LCV Trucks" in result["extracted_text"]
        assert result["file_type"] == ".txt"
        
        print(f"✅ Success! Extracted: {len(result['extracted_text'])} chars.")
        print(f"   FileType Detected: {result['file_type']}")

    except Exception as e:
        print(f"❌ FAILED: {e}")

    # Scenario B: Missing File (Should Raise Error)
    try:
        print(f"\n[Test B] Input: missing_file.pdf")
        bad_state = initial_state.copy()
        bad_state["file_path"] = "missing_file.pdf"
        parse_document(bad_state)
        print("❌ FAILED: Should have raised FileNotFoundError")
    except FileNotFoundError:
        print("✅ Success! Correctly caught missing file.")
    except Exception as e:
        print(f"❌ FAILED: Wrong error raised: {e}")

    # Clean up
    cleanup_dummy_files()
    logger.info(">>> NODE 1 TEST COMPLETE <<<\n")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    # Uncomment lines below as we add more nodes
    test_parse_node()
    # test_extraction_node()
    # test_validation_node()