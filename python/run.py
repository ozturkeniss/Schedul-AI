#!/usr/bin/env python3
"""
AI Scheduler Python Server Entry Point
"""

import os
import sys
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from api.app import AISchedulerAPI
from config import config
import structlog

logger = structlog.get_logger()

def main():
    """Main entry point for AI Scheduler Python server"""
    try:
        logger.info("Starting AI Scheduler Python Server", config=config.to_dict())
        
        # Create API server
        api = AISchedulerAPI()
        
        # Run server
        api.run(
            host=config.api.host,
            port=config.api.port
        )
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error("Server failed to start", error=str(e))
        sys.exit(1)

if __name__ == '__main__':
    main() 