# file: main.py
import os
import sys
from langgraph.graph import StateGraph, END
# from langchain_core.runnables.graph import MermaidDrawMethod
from Xfrate2.utils import logger
from Xfrate2.state import AgentState

# --- IMPORT NODES ---
# We assume your nodes are in the 'nodes' folder. 
# Make sure you have an empty __init__.py in the 'nodes' folder to make it a package.
from Xfrate2.nodes.file_reader import parse_document      # Node 1
from Xfrate2.nodes.extractor import extract_order    # Node 2
from Xfrate2.nodes.validate_node import validate_data   # Node 3
from Xfrate2.nodes.finalize_node import finalize_and_route # Node 4


def build_agent():
    """
    Constructs the Phase 1 FTL Order Extraction Graph.
    Flow: Parse -> Extract -> Validate -> Finalize -> END
    """
    # 1. Initialize the Graph with the State Schema
    workflow = StateGraph(AgentState)

    # 2. Add Nodes
    workflow.add_node("parse_node", parse_document)
    workflow.add_node("extract_node", extract_order)
    workflow.add_node("validate_node", validate_data)
    workflow.add_node("finalize_node", finalize_and_route)

    # 3. Define Edges (The Flow)
    workflow.set_entry_point("parse_node")
    
    workflow.add_edge("parse_node", "extract_node")
    workflow.add_edge("extract_node", "validate_node")
    workflow.add_edge("validate_node", "finalize_node")
    workflow.add_edge("finalize_node", END)

    # 4. Compile
    app = workflow.compile()
    return app

def run_pipeline(file_path: str):
    """
    Helper to run the agent on a single file.
    """
    logger.info(f"Starting Pipeline for: {file_path}")
    
    if not os.path.exists(file_path):
        logger.error("File does not exist.")
        return

    # Initialize State
    initial_state = {
        "file_path": file_path,
        "extracted_text": "",
        "file_type": "",
        "raw_extraction": {},
        "validation_errors": [],
        "human_corrections": [],
        "final_orders": []
    }

    # Run the Graph
    app = build_agent()
    result = app.invoke(initial_state)
    
    logger.info("Pipeline Finished.")
    return result

# --- EXECUTION BLOCK ---
if __name__ == "__main__":
    # Create a dummy file if you don't have one to test immediately
    # test_file = "Xfrate2/input/FileB.pdf"
    # print("Hello")
    files=["Xfrate2/input/FileA.docx","Xfrate2/input/FileA.pdf","Xfrate2/input/FileB.pdf","Xfrate2/input/FileC.png","Xfrate2/input/FileD (1).docx","Xfrate2/input/FileD (2).docx","Xfrate2/input/FileD (3).pdf","Xfrate2/input/FileD.docx","Xfrate2/input/FileE.png"]
    for file in files:
        if not os.path.exists(file):
            print(f"{file}: No such file")
        run_pipeline(file)