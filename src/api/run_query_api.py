#!/usr/bin/env python3
"""
Run the minimal query API.
Starts FastAPI app that exposes health and /api/v1/search.
"""
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

import uvicorn
from src.api.api import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
