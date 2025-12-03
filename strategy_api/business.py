import json
import os
from datetime import datetime

# File paths for data storage
DATA_DIR = "data"
POSITIONS_FILE = os.path.join(DATA_DIR, "current_positions.json")
HISTORY_FILE = os.path.join(DATA_DIR, "trading_history.json")

def analyze_tick(payload: dict) -> dict:
    """
    Business layer function to analyze trading tick data.
    Calculates unrealized P&L for current positions.
    
    Args:
        payload: Dictionary containing Positions, Market_Summary, and market_history
        
    Returns:
        Dictionary with result, summary, and decisions
    """
    positions = payload.get("Positions", [])
    market_summary = payload.get("Market_Summary", [])
    
    # Create a lookup dictionary for current prices
    current_prices = {
        item["ticker"]: float(item["current_price"]) 
        for item in market_summary
    }
    
    # Calculate unrealized P&L
    unrealized_pnl = 0.0
    positions_evaluated = 0
    
    for position in positions:
        ticker = position["ticker"]
        quantity = float(position["quantity"])
        purchase_price = float(position["purchase_price"])
        
        # Check if we have current price for this ticker
        if ticker in current_prices:
            current_price = current_prices[ticker]
            # P&L = (current_price - purchase_price) * quantity
            pnl = (current_price - purchase_price) * quantity
            unrealized_pnl += pnl
            positions_evaluated += 1
    
    # Return structured response
    return {
        "result": "success",
        "summary": {
            "positions_evaluated": positions_evaluated,
            "unrealized_pnl": unrealized_pnl
        },
        "decisions": []  # Placeholder for Part 3 trade logic
    }

# NEW FUNCTIONS FOR ASSIGNMENT 6

def load_json_file(filepath):
    """Load data from JSON file"""
    if not os.path.exists(filepath):
        return []  # Return empty array if file doesn't exist
    
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []  # Return empty array if file is corrupted

def save_json_file(filepath, data):
    """Save data to JSON file"""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

def update_current_positions(tick_data):
    """
    Update the current positions file with new market data.
    This is a full replace operation - updates existing positions or adds new ones.
    
    Args:
        tick_data: Dictionary with ticker, price, quantity, purchase_price
        
    Returns:
        Previous price for the ticker (or None if first time seeing it)
    """
    positions = load_json_file(POSITIONS_FILE)
    
    ticker = tick_data.get('ticker')
    new_price = tick_data.get('price')
    quantity = tick_data.get('quantity')
    purchase_price = tick_data.get('purchase_price')
    
    # Find and update the position
    old_price = None
    position_found = False
    
    for position in positions:
        if position['ticker'] == ticker:
            old_price = position['current_price']
            position['current_price'] = new_price
            
            # Recalculate unrealized P&L
            position['unrealized_pnl'] = round(
                (new_price - position['purchase_price']) * position['quantity'], 
                2
            )
            
            position_found = True
            break
    
    # If position doesn't exist, create it
    if not position_found:
        positions.append({
            'ticker': ticker,
            'quantity': quantity,
            'purchase_price': purchase_price,
            'current_price': new_price,
            'unrealized_pnl': 0.0
        })
        old_price = new_price  # First time seeing this ticker
    
    # Save updated positions
    save_json_file(POSITIONS_FILE, positions)
    return old_price

def execute_trading_strategy(tick_data, previous_price):
    """
    Simple "dumb" trading strategy for Assignment 6:
    - If price goes UP: log a SELL transaction
    - If price goes DOWN or SAME: log a TICK_UPDATE (equivalent to STAY)
    
    Args:
        tick_data: Dictionary with ticker, price, quantity
        previous_price: The previous price for comparison
        
    Returns:
        Action taken ('SELL', 'STAY', or 'INITIAL')
    """
    current_price = tick_data.get('price')
    ticker = tick_data.get('ticker')
    quantity = tick_data.get('quantity')
    
    if previous_price is None:
        # First tick for this ticker - don't log anything
        return 'INITIAL'
    
    if current_price > previous_price:
        # Price went UP - SELL
        log_transaction(
            action='SELL',
            ticker=ticker,
            price=current_price,
            quantity=quantity,
            note='Price increased - sell signal'
        )
        return 'SELL'
    else:
        # Price went DOWN or stayed same - STAY (log as TICK_UPDATE)
        log_transaction(
            action='TICK_UPDATE',
            ticker=ticker,
            price=current_price,
            quantity=None,  # TICK_UPDATE doesn't need quantity
            note='Price decreased - stay'
        )
        return 'STAY'

def log_transaction(action, ticker, price, note, quantity=None):
    """
    Log a transaction to the trading history file.
    
    Args:
        action: 'BUY', 'SELL', or 'TICK_UPDATE'
        ticker: Stock ticker symbol
        price: Transaction price
        note: Description of the transaction
        quantity: Number of shares (optional, not used for TICK_UPDATE)
    """
    history = load_json_file(HISTORY_FILE)
    
    transaction = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'ticker': ticker,
        'action': action,
        'price': round(price, 2),
        'note': note
    }
    
    # Only add quantity for BUY/SELL actions (not for TICK_UPDATE)
    if quantity is not None:
        transaction['quantity'] = quantity
    
    history.append(transaction)
    save_json_file(HISTORY_FILE, history)