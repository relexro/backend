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

# Define paths
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'agent-config')
AGENT_LOOP_PATH = os.path.join(CONFIG_DIR, 'agent_loop.txt')
TOOLS_PATH = os.path.join(CONFIG_DIR, 'tools.json')
PROMPT_PATH = os.path.join(CONFIG_DIR, 'prompt.txt')
MODULES_PATH = os.path.join(CONFIG_DIR, 'modules.txt')

class ConfigLoadError(Exception):
    """Custom exception for configuration loading errors."""
    pass

def load_agent_loop() -> str:
    """
    Load the agent loop description from agent_loop.txt.
    
    Returns:
        The content of agent_loop.txt as a string
    """
    try:
        with open(AGENT_LOOP_PATH, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error loading agent loop configuration: {str(e)}")
        raise ConfigLoadError(f"Failed to load agent loop configuration: {str(e)}")

def load_tools() -> List[Dict[str, Any]]:
    """
    Load tool definitions from tools.json.
    
    Returns:
        A list of tool definitions
    """
    try:
        with open(TOOLS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading tool definitions: {str(e)}")
        raise ConfigLoadError(f"Failed to load tool definitions: {str(e)}")

def load_prompts() -> Dict[str, str]:
    """
    Load prompt templates from prompt.txt.
    
    Returns:
        A dictionary of prompt templates with keys based on section names
    """
    try:
        with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the prompt file into sections
        prompts = {}
        current_section = None
        current_content = []
        
        for line in content.split('\n'):
            if line.startswith('# ---') and '---' in line:
                # New section header
                if current_section and current_content:
                    prompts[current_section] = '\n'.join(current_content).strip()
                    current_content = []
                
                # Extract section name
                section_name = line.split('---')[1].strip()
                current_section = section_name
            elif line.startswith('"""') and current_section:
                # Start or end of content block
                continue
            elif current_section:
                # Content line
                current_content.append(line)
        
        # Add the last section
        if current_section and current_content:
            prompts[current_section] = '\n'.join(current_content).strip()
        
        return prompts
    except Exception as e:
        logger.error(f"Error loading prompt templates: {str(e)}")
        raise ConfigLoadError(f"Failed to load prompt templates: {str(e)}")

def load_modules() -> Dict[str, str]:
    """
    Load module descriptions from modules.txt.
    
    Returns:
        A dictionary of module descriptions with keys based on XML tags
    """
    try:
        with open(MODULES_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
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
        
        return modules
    except Exception as e:
        logger.error(f"Error loading module descriptions: {str(e)}")
        raise ConfigLoadError(f"Failed to load module descriptions: {str(e)}")

def get_system_prompt() -> str:
    """
    Get the system prompt for Gemini.
    
    Returns:
        The formatted system prompt
    """
    try:
        prompts = load_prompts()
        modules = load_modules()
        
        # Get the base system prompt
        system_prompt = prompts.get('Gemini System Prompt', '')
        
        # Enhance with modules content
        for module_name, module_content in modules.items():
            if module_name in ['intro', 'language_settings', 'system_capability', 'agent_loop', 
                              'llm_collaboration_rules', 'context_management_rules', 'tool_use_rules',
                              'legal_research_rules', 'drafting_rules', 'message_rules', 'error_handling']:
                system_prompt += f"\n\n# {module_name.replace('_', ' ').title()}\n{module_content}"
        
        return system_prompt
    except Exception as e:
        logger.error(f"Error generating system prompt: {str(e)}")
        raise ConfigLoadError(f"Failed to generate system prompt: {str(e)}")

def get_grok_prompt_template() -> str:
    """
    Get the prompt template for Grok consultation.
    
    Returns:
        The formatted Grok prompt template
    """
    try:
        prompts = load_prompts()
        return prompts.get('Grok Consultation Prompt Template', '')
    except Exception as e:
        logger.error(f"Error getting Grok prompt template: {str(e)}")
        raise ConfigLoadError(f"Failed to get Grok prompt template: {str(e)}")

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
        return {
            'agent_loop': load_agent_loop(),
            'tools': load_tools(),
            'prompts': load_prompts(),
            'modules': load_modules()
        }
    except Exception as e:
        logger.error(f"Error loading all configurations: {str(e)}")
        raise ConfigLoadError(f"Failed to load all configurations: {str(e)}")
