#!/usr/bin/env python
"""
Direct test for the agent node creation and config paths
This bypasses functions_framework to test only the critical parts
"""
import logging
import sys
import os
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the functions/src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'functions/src'))

def test_agent_config():
    """Test loading the agent configuration"""
    try:
        from agent_config import (
            load_agent_loop, 
            load_tools, 
            load_prompts, 
            load_modules,
            get_system_prompt
        )
        
        logger.info("Testing agent_config.py loading functions...")
        
        # Test loading each config component
        logger.info("Loading agent loop...")
        agent_loop = load_agent_loop()
        logger.info(f"Agent loop loaded successfully. Length: {len(agent_loop)} characters")
        
        logger.info("Loading tools...")
        tools = load_tools()
        logger.info(f"Tools loaded successfully. Count: {len(tools)} tools")
        
        logger.info("Loading prompts...")
        prompts = load_prompts()
        logger.info(f"Prompts loaded successfully. Sections: {list(prompts.keys())}")
        
        logger.info("Loading modules...")
        modules = load_modules()
        logger.info(f"Modules loaded successfully. Sections: {list(modules.keys())}")
        
        logger.info("Loading system prompt...")
        system_prompt = get_system_prompt()
        logger.info(f"System prompt loaded successfully. Length: {len(system_prompt)} characters")
        
        return {
            "status": "success",
            "agent_loop_length": len(agent_loop),
            "tool_count": len(tools),
            "prompt_sections": list(prompts.keys()),
            "module_sections": list(modules.keys()),
            "system_prompt_length": len(system_prompt)
        }
    except Exception as e:
        logger.error(f"Error testing agent config: {str(e)}", exc_info=True)
        return {"status": "error", "error": str(e)}

def test_agent_nodes():
    """Test creating the agent graph"""
    try:
        from agent_nodes import create_agent_graph
        
        logger.info("Testing agent_nodes.py create_agent_graph function...")
        
        # Create the agent graph
        agent_graph = create_agent_graph()
        
        logger.info("Agent graph created successfully")
        
        return {
            "status": "success",
            "message": "Agent graph created successfully"
        }
    except Exception as e:
        logger.error(f"Error creating agent graph: {str(e)}", exc_info=True)
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    print("\n=== Testing Agent Configuration ===")
    config_result = test_agent_config()
    print(f"Config test result: {json.dumps(config_result, indent=2)}")
    
    print("\n=== Testing Agent Graph Creation ===")
    nodes_result = test_agent_nodes()
    print(f"Agent nodes test result: {json.dumps(nodes_result, indent=2)}") 