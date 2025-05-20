"""
Agent Configuration - Loads and manages configurations from agent-config directory
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define paths - Use a robust path construction relative to the current script
_CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_AGENT_CONFIG_DIR = os.path.join(_CURRENT_SCRIPT_DIR, 'agent-config')
logger.info(f"Agent config calculated CONFIG_DIR: {os.path.abspath(_AGENT_CONFIG_DIR)}")
AGENT_LOOP_PATH = os.path.join(_AGENT_CONFIG_DIR, 'agent_loop.txt')
TOOLS_PATH = os.path.join(_AGENT_CONFIG_DIR, 'tools.json')
MODULES_PATH = os.path.join(_AGENT_CONFIG_DIR, 'modules.txt')

class ConfigLoadError(Exception):
    """Custom exception for configuration loading errors."""
    pass

def load_agent_loop() -> str:
    """
    Load the agent loop description from agent_loop.txt.

    Returns:
        The content of agent_loop.txt as a string
    """
    file_path = AGENT_LOOP_PATH
    logger.info(f"Attempting to load agent loop from: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            logger.info(f"Successfully loaded agent loop from: {file_path}")
            return content
    except FileNotFoundError:
        abs_path = os.path.abspath(file_path)
        logger.error(f"FileNotFoundError: Could not find agent loop config file at expected path: {abs_path}")
        raise ConfigLoadError(f"Agent loop configuration file not found at: {abs_path}")
    except Exception as e:
        logger.error(f"Error loading agent loop configuration from {file_path}: {str(e)}")
        raise ConfigLoadError(f"Failed to load agent loop configuration: {str(e)}")

def load_tools() -> List[Dict[str, Any]]:
    """
    Load tool definitions from tools.json.

    Returns:
        A list of tool definitions
    """
    file_path = TOOLS_PATH
    logger.info(f"Attempting to load tools from: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tools_data = json.load(f)
            logger.info(f"Successfully loaded tools from: {file_path}")
            return tools_data
    except FileNotFoundError:
        abs_path = os.path.abspath(file_path)
        logger.error(f"FileNotFoundError: Could not find tools config file at expected path: {abs_path}")
        raise ConfigLoadError(f"Tools configuration file not found at: {abs_path}")
    except Exception as e:
        logger.error(f"Error loading tool definitions from {file_path}: {str(e)}")
        raise ConfigLoadError(f"Failed to load tool definitions: {str(e)}")



def load_modules() -> Dict[str, str]:
    """
    Load module descriptions from modules.txt.

    Returns:
        A dictionary of module descriptions with keys based on XML tags
    """
    file_path = MODULES_PATH
    logger.info(f"Attempting to load modules from: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            logger.info(f"Successfully read modules file from: {file_path}")

        # Parse the modules file into sections based on XML-like tags
        modules = {}
        current_tag = None
        current_content = []

        for line in content.split('\n'):
            if line.startswith('<') and '>' in line and not line.startswith('</'):
                # New tag
                if current_tag and current_content:
                    modules[current_tag] = '\n'.join(current_content).strip()
                    current_content = []

                # Extract tag name
                tag = line.strip('<>').strip()
                current_tag = tag
            elif line.startswith('</') and current_tag:
                # End of tag
                if current_tag and current_content:
                    modules[current_tag] = '\n'.join(current_content).strip()
                    current_content = []
                current_tag = None
            elif current_tag:
                # Content line
                current_content.append(line)

        # Add the last section if any
        if current_tag and current_content:
            modules[current_tag] = '\n'.join(current_content).strip()

        logger.info(f"Successfully parsed modules from: {file_path}")
        return modules
    except FileNotFoundError:
        abs_path = os.path.abspath(file_path)
        logger.error(f"FileNotFoundError: Could not find modules config file at expected path: {abs_path}")
        raise ConfigLoadError(f"Modules configuration file not found at: {abs_path}")
    except Exception as e:
        logger.error(f"Error loading module descriptions from {file_path}: {str(e)}")
        raise ConfigLoadError(f"Failed to load module descriptions: {str(e)}")

def get_system_prompt(prompt_type: str = "main") -> str:
    """
    Get the system prompt. Always uses agent_loop.txt as the primary source.

    Args:
        prompt_type: The type of prompt to get. Currently only "main" is fully supported.
                    Other values will return a generic fallback prompt.

    Returns:
        The formatted system prompt
    """
    logger.info(f"Generating system prompt for prompt_type: '{prompt_type}'")
    try:
        if prompt_type == "main":
            # For the main prompt, use agent_loop.txt directly
            main_prompt_content = load_agent_loop()
            logger.info(f"Using agent_loop.txt content for 'main' system prompt.")
            return main_prompt_content
        else:
            # For any other prompt type, use a generic fallback
            logger.info(f"Requested prompt_type '{prompt_type}' is not specifically supported. Using generic fallback.")
            return f"You are a helpful legal assistant specialized in {prompt_type}. Please provide detailed and structured assistance."
    except ConfigLoadError as e:
        logger.error(f"CRITICAL: ConfigLoadError generating system prompt for '{prompt_type}', likely from load_agent_loop(): {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating system prompt for '{prompt_type}': {str(e)}")
        raise ConfigLoadError(f"Unexpected error in get_system_prompt for '{prompt_type}': {str(e)}")

def load_system_prompt() -> str:
    """
    Load the main system prompt.
    Alias for get_system_prompt("main") for backward compatibility.

    Returns:
        The main system prompt
    """
    return get_system_prompt("main")

def get_grok_prompt_template() -> str:
    """
    Get the prompt template for Grok consultation.

    Returns:
        The formatted Grok prompt template
    """
    # Standard Grok consultation template in Romanian
    return "Aceasta este o consultare pentru Grok. Te rog să analizezi următoarele informații și să oferi o perspectivă juridică strategică: {{context}}"

def get_tool_by_name(tool_name: str) -> Optional[Dict[str, Any]]:
    """
    Get a tool definition by name.

    Args:
        tool_name: The name of the tool to retrieve

    Returns:
        The tool definition or None if not found
    """
    try:
        tools = load_tools()
        for tool in tools:
            if tool.get('function', {}).get('name') == tool_name:
                return tool
        return None
    except Exception as e:
        logger.error(f"Error getting tool definition: {str(e)}")
        raise ConfigLoadError(f"Failed to get tool definition: {str(e)}")

def get_all_configs() -> Dict[str, Any]:
    """
    Get all configurations in a single dictionary.

    Returns:
        A dictionary containing all configurations
    """
    try:
        configs = {}

        # Critical configurations that should raise errors if missing
        try:
            configs['agent_loop'] = load_agent_loop()
        except Exception as e:
            logger.error(f"Critical error loading agent_loop: {str(e)}")
            raise

        try:
            configs['tools'] = load_tools()
        except Exception as e:
            logger.error(f"Critical error loading tools: {str(e)}")
            raise

        # Non-critical configurations that can return empty/default values
        try:
            configs['modules'] = load_modules()
        except Exception as e:
            logger.error(f"Error loading modules: {str(e)}")
            configs['modules'] = {}

        return configs
    except Exception as e:
        logger.error(f"Error loading all configurations: {str(e)}")
        raise ConfigLoadError(f"Failed to load all configurations: {str(e)}")

# Language Configuration
SUPPORTED_USER_LANGUAGES = [
    "romanian", "english", "french", "german", "italian", "spanish",
    "sweden", "norway", "denmark", "ukrainian", "polish", "hungarian",
    "greek", "turkey", "hebrew", "arab", "portuguese", "nederland",
    "estonian", "finland", "czechia", "slovakia", "lithuanian",
    "iceland", "latvia", "bulgarian", "serbian", "macedonian", "albanian"
]

UI_LANGUAGES = ["en", "ro"]

INTERNAL_OPERATIONAL_LANGUAGE = "ro"
