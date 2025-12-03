import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define the trading tool for ChatGPT
TRADING_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "make_trade_recommendation",
            "description": "Analyze stock data and recommend trading actions (BUY, SELL, or STAY) for each position",
            "parameters": {
                "type": "object",
                "properties": {
                    "trades": {
                        "type": "array",
                        "description": "List of trade recommendations",
                        "items": {
                            "type": "object",
                            "properties": {
                                "action": {
                                    "type": "string",
                                    "enum": ["BUY", "SELL", "STAY"],
                                    "description": "The trading action to take"
                                },
                                "ticker": {
                                    "type": "string",
                                    "description": "The stock ticker symbol"
                                },
                                "quantity": {
                                    "type": "integer",
                                    "description": "The quantity to trade (0 for STAY)"
                                }
                            },
                            "required": ["action", "ticker", "quantity"]
                        }
                    }
                },
                "required": ["trades"]
            }
        }
    }
]


def get_chatgpt_recommendation(tick_data):
    """
    Send tick data to ChatGPT and get trading recommendations.
    
    Args:
        tick_data (dict): The tick payload containing POSITIONS and DAY
        
    Returns:
        list: List of trade recommendations with action, ticker, and quantity
    """
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file")
    
    # Create the prompt for ChatGPT
    prompt = f"""
    Analyze the following stock positions and market data, then provide trading recommendations.
    
    Current Positions: {json.dumps(tick_data.get('POSITIONS', []), indent=2)}
    Market Summary: {json.dumps(tick_data.get('Market_Summary', []), indent=2)}
    Market History: {json.dumps(tick_data.get('market_history', []), indent=2)}
    Date: {tick_data.get('DAY', 'Unknown')}
    
    For each position, decide whether to:
    - BUY: Purchase more shares (specify quantity)
    - SELL: Sell shares (specify quantity)
    - STAY: Hold current position (quantity = 0)
    
    Use the make_trade_recommendation function to provide your recommendations.
    """
    
    url = "https://api.openai.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-5-nano",
        "messages": [
            {
                "role": "system",
                "content": "You are a trading assistant that analyzes stock positions and provides buy/sell recommendations."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "tools": TRADING_TOOLS,
        "tool_choice": "auto"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        message = result['choices'][0]['message']
        
        # Check if ChatGPT used the tool
        if message.get('tool_calls'):
            tool_call = message['tool_calls'][0]
            function_args = json.loads(tool_call['function']['arguments'])
            return function_args.get('trades', [])
        else:
            # If no tool call, return empty recommendations
            return []
    
    except Exception as e:
        print(f"Error getting ChatGPT recommendation: {e}")
        return []


def post_trade_to_mothership(trade_id, trades):
    """
    Post trade recommendations to the mothership API.
    
    Args:
        trade_id (str): The unique ID from the /tick path parameter
        trades (list): List of trade recommendations
        
    Returns:
        dict: Response from the mothership API with updated positions
    """
    api_key = os.getenv("MOTHERSHIP_API_KEY")
    base_url = os.getenv("MOTHERSHIP_BASE_URL", "https://mothership-crg7hzedd6ckfegv.eastus-01.azurewebsites.net")
    
    if not api_key:
        raise ValueError("MOTHERSHIP_API_KEY not found in .env file")
    
    url = f"{base_url}/make_trade"
    
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "id": trade_id,
        "trades": trades
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        return response.json()
    
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def get_mothership_positions():
    """
    Fetch current positions from the mothership API.
    
    Returns:
        dict: Current positions from mothership
    """
    api_key = os.getenv("MOTHERSHIP_API_KEY")
    positions_url = os.getenv("MOTHERSHIP_POSITIONS_URL", "https://mothership-crg7hzedd6ckfegv.eastus-01.azurewebsites.net/positions")
    
    if not api_key:
        return {"error": "MOTHERSHIP_API_KEY not found in .env file"}
    
    headers = {
        "x-api-key": api_key
    }
    
    try:
        response = requests.get(positions_url, headers=headers)
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def process_tick_with_ai(tick_data, trade_id):
    """
    Main function to process a tick with AI recommendations.
    
    Args:
        tick_data (dict): The tick payload
        trade_id (str): The unique ID from the /tick path parameter
        
    Returns:
        tuple: (recommendations, updated_positions)
    """
    # Get AI recommendations
    recommendations = get_chatgpt_recommendation(tick_data)
    
    if not recommendations:
        return [], {"error": "No recommendations received from AI"}
    
    # Post to mothership and get updated positions
    result = post_trade_to_mothership(trade_id, recommendations)
    
    return recommendations, result