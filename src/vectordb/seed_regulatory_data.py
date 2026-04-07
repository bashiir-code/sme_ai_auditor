"""
seed_regulatory_data.py
------------------------
Utility script to populate the Qdrant Vector Database with the 
official EU AI Act and Data Act context.
"""

import os
import sys
from dotenv import load_dotenv
import structlog

# Ensure we have our environment variables
load_dotenv()

from src.vectordb.index_manager import IndexManager

logger = structlog.get_logger(__name__)

def seed_regulatory_context():
    """
    Sequentially crawls the data/ folders and indexes regulatory provisions.
    """
    logger.info("Starting Regulatory Context Seeding Sequence")
    
    # Initialize the Pilot's Index Manager
    try:
        manager = IndexManager()
    except Exception as e:
        logger.error("Failed to initialize IndexManager", error=str(e))
        sys.exit(1)
        
    # Registry of folders and their semantic tags
    regulatory_targets = [
        {"path": "data/eu_ai_act", "tag": "eu_ai_act"},
        {"path": "data/eu_data_act", "tag": "eu_data_act"},
        {"path": "data/cen_cenelec_standards", "tag": "cen_standards"}
    ]
    
    total_indexed = 0
    
    for target in regulatory_targets:
        folder_path = target["path"]
        source_tag = target["tag"]
        
        if not os.path.exists(folder_path):
            logger.warning("Folder not found. Skipping.", path=folder_path)
            continue
            
        logger.info("Indexing Regulatory Folder", path=folder_path, tag=source_tag)
        
        # Iterate over all files in the folder
        for file_name in os.listdir(folder_path):
            if file_name.endswith((".pdf", ".docx", ".txt", ".md")):
                full_path = os.path.join(folder_path, file_name)
                try:
                    logger.info("Processing document...", file=file_name)
                    chunks_count = manager.index_document(
                        file_path=full_path, 
                        document_source=source_tag
                    )
                    total_indexed += chunks_count
                    logger.info("Indexed successfully", file=file_name, count=chunks_count)
                except Exception as e:
                    logger.error("Failed to index document", file=file_name, error=str(e))
    
    logger.info("Regulatory Seeding Sequence Complete!", total_chunks=total_indexed)

if __name__ == "__main__":
    seed_regulatory_context()
