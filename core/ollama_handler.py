
import ollama
import json
from . import actions
from .car_state import CarState
from . import config

# Define available tools schema for context
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "set_ac",
            "description": "Control the Air Conditioning",
            "parameters": {
                "type": "object",
                "properties": {
                    "on": {"type": "string", "enum": ["on", "off"]},
                    "temperature": {"type": "integer", "description": "Target temperature in Celsius"}
                },
                "required": ["on"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "navigate_to",
            "description": "Set navigation destination",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "The destination address or name"}
                },
                "required": ["destination"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "toggle_lights",
            "description": "Turn headlights on or off",
            "parameters": {
                "type": "object",
                "properties": {
                    "on": {"type": "string", "enum": ["on", "off"]}
                },
                "required": ["on"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "toggle_wipers",
            "description": "Turn wipers on or off",
            "parameters": {
                "type": "object",
                "properties": {
                    "on": {"type": "string", "enum": ["on", "off"]}
                },
                "required": ["on"]
            }
        }
    }
]


# System Prompt optimized for small models (1B/2B parameters)
SYSTEM_PROMPT = """
You are a car assistant. You can control:

1. AC (on/off, temperature) -> distinct tool "ac"
2. LIGHTS (on/off) -> distinct tool "lights" 
3. WIPERS (on/off) -> distinct tool "wipers"
4. NAVIGATE (destination) -> distinct tool "nav"


When the user asks for an action, response ONLY with a JSON object like:
{"tool": "ac", "args": {"on": "on", "temperature": 22}}
{"tool": "lights", "args": {"on": "on"}}
{"tool": "lights", "args": {"on": "off"}}
{"tool": "wipers", "args": {"on": "on"}}
{"tool": "wipers", "args": {"on": "off"}}
{"tool": "nav", "args": {"destination": "Home"}}

If it's just a question, reply normally.
"""

def process_command(text: str, state: CarState) -> str:
    """
    Process the user's text command using Ollama and execute any tools.
    """
    model = config.OLLAMA_MODEL
    
    messages = [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': text}
    ]

    try:
        response = ollama.chat(model=model, messages=messages)
        content = response['message']['content']
        
        # Strip code blocks if present
        if "```json" in content:
            content = content.replace("```json", "").replace("```", "")
        elif "```" in content:
            content = content.replace("```", "")
            
        # Check for JSON tool call
        try:
            # simple heuristic to find json
            if "{" in content and "}" in content:
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                json_str = content[json_start:json_end]
                
                tool_call = json.loads(json_str)
                
                if "tool" in tool_call and "args" in tool_call:
                    tool_name = tool_call["tool"]
                    tool_args = tool_call["args"]
                    
                    print(f"Ollama Calling Tool: {tool_name} with {tool_args}")
                    
                    if tool_name == "ac" or tool_name == "set_ac":
                        return actions.set_ac(state, **tool_args)
                    elif tool_name == "nav" or tool_name == "navigate_to":
                        return actions.navigate_to(state, **tool_args)
                    elif tool_name == "lights" or tool_name == "toggle_lights":
                        return actions.toggle_lights(state, **tool_args)
                    elif tool_name == "wipers" or tool_name == "toggle_wipers":
                        return actions.toggle_wipers(state, **tool_args)
                    else:
                        return f"Unknown tool: {tool_name}"
            
            # If no JSON or parsing failed/not a tool call, return text
            return content

        except json.JSONDecodeError:
            return content
            
    except Exception as e:
        print(f"Ollama Error: {e}")
        return "I'm having trouble connecting to my local brain."
