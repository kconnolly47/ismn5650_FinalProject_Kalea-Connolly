# validators.py (snippet)
from datetime import datetime

def _is_iso_date(s: str) -> bool:
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except Exception:
        return False

# ... inside validate_tick_payload for market_history:
    if "market_history" not in payload or not isinstance(payload["market_history"], list):
        return False, "Invalid payload: 'market_history' must be a list"
    for i, h in enumerate(payload["market_history"]):
        if not isinstance(h, dict):
            return False, f"Invalid payload: market_history[{i}] must be an object"
        if "ticker" not in h or not isinstance(h["ticker"], str) or not h["ticker"].strip():
            return False, f"Invalid payload: market_history[{i}].ticker must be a non-empty string"
        if "price" not in h or not _is_number(h["price"]):
            return False, f"Invalid payload: market_history[{i}].price must be a number"
        # NEW: expect a string date, not an int
        if "day" not in h or not isinstance(h["day"], str) or not _is_iso_date(h["day"]):
            return False, f"Invalid payload: market_history[{i}].day must be 'YYYY-MM-DD' string"


def validate_tick_payload(payload: dict) -> tuple:
    """
    Validates the /tick endpoint payload.
    
    Args:
        payload: The JSON payload from the request
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    if not isinstance(payload, dict):
        return (False, "Payload must be a JSON object")
    
    # Check required top-level keys
    required_keys = ["Positions", "Market_Summary", "market_history"]
    for key in required_keys:
        if key not in payload:
            return (False, f"Missing required field: {key}")
    
    # Validate Positions
    positions = payload["Positions"]
    if not isinstance(positions, list):
        return False, "Positions must be a list"
    if len(positions) == 0:
        return False, "Positions must be a non-empty list"
    
    for i, pos in enumerate(positions):
        if not isinstance(pos, dict):
            return False, f"Position at index {i} must be an object"
        
        # Check required fields in each position
        pos_fields = ["ticker", "quantity", "purchase_price"]
        for field in pos_fields:
            if field not in pos:
                return False, f"Position at index {i} missing field: {field}"
        
        # Validate types
        if not isinstance(pos["ticker"], str):
            return False, f"Position at index {i}: ticker must be a string"
        try:
            float(pos["quantity"])
            float(pos["purchase_price"])
        except (ValueError, TypeError):
            return False, f"Position at index {i}: quantity and purchase_price must be numeric"
    
    # Validate Market_Summary
    market_summary = payload["Market_Summary"]
    if not isinstance(market_summary, list):
        return False, "Market Summary must be a list"
    if len(market_summary) == 0:
        return False, "Market Summary must be a non-empty list"
    
    for i, item in enumerate(market_summary):
        if not isinstance(item, dict):
            return False, f"Market Summary item at index {i} must be an object"
        
        # Check required fields
        if "ticker" not in item or "current_price" not in item:
            return False, f"Market Summary item at index {i} missing required fields"
        
        if not isinstance(item["ticker"], str):
            return False, f"Market Summary at index {i}: ticker must be a string"
        try:
            float(item["current_price"])
        except (ValueError, TypeError):
            return False, f"Market Summary at index {i}: current_price must be numeric"
    
    # Validate market_history
    market_history = payload["market_history"]
    if not isinstance(market_history, list):
        return False, "market_history must be a list"
    # market_history can be empty, so we don't check length
    
    for i, item in enumerate(market_history):
        if not isinstance(item, dict):
            return False, f"market_history item at index {i} must be an object"
        
        # Check required fields
        hist_fields = ["ticker", "price", "day"]
        for field in hist_fields:
            if field not in item:
                return False, f"market_history item at index {i} missing field: {field}"
        
        if not isinstance(item["ticker"], str):
            return False, f"market_history at index {i}: ticker must be a string"
        try:
            float(item["price"])
            int(item["day"])
        except (ValueError, TypeError):
            return False, f"market_history at index {i}: price must be numeric and day must be an integer"
    
    return True, ""
