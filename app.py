from flask import Flask, request, jsonify, render_template_string
import json
import os
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv
from ai_module import process_tick_with_ai, get_mothership_positions  # Import your AI module

# Load environment variables
load_dotenv()

app = Flask(__name__)

# File paths
POSITIONS_FILE = "positions.json"
TRADING_LOG_FILE = "trading_log.json"

# API Key from environment
API_KEY = os.getenv("API_KEY")

# Authentication decorator
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        provided_key = request.headers.get('apikey')
        
        # Debug print
        print(f"Expected API_KEY: {API_KEY}")
        print(f"Provided API Key: {provided_key}")
        
        if not API_KEY:
            return jsonify({"result": "failure", "error": "Server API key not configured"}), 500
        
        if provided_key != API_KEY:
            return jsonify({"result": "failure", "error": "Invalid API key"}), 401
        return f(*args, **kwargs)
    return decorated_function

# Helper functions
def load_positions():
    """Load current positions from file"""
    if os.path.exists(POSITIONS_FILE):
        with open(POSITIONS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_positions(positions):
    """Save positions to file"""
    with open(POSITIONS_FILE, 'w') as f:
        json.dump(positions, f, indent=2)

def load_trading_log():
    """Load trading log from file"""
    if os.path.exists(TRADING_LOG_FILE):
        with open(TRADING_LOG_FILE, 'r') as f:
            return json.load(f)
    return []

def save_trading_log(log):
    """Save trading log to file"""
    with open(TRADING_LOG_FILE, 'w') as f:
        json.dump(log, f, indent=2)

def calculate_unrealized_pnl(positions, market_summary):
    """Calculate unrealized P&L based on current market prices"""
    # Create a mapping of ticker to current price
    current_prices = {item['ticker']: float(item['current_price']) 
                     for item in market_summary}
    
    total_pnl = 0.0
    for position in positions:
        ticker = position['ticker']
        quantity = float(position['quantity'])
        purchase_price = float(position['purchase_price'])
        
        if ticker in current_prices:
            current_price = current_prices[ticker]
            pnl = (current_price - purchase_price) * quantity
            total_pnl += pnl
    
    return total_pnl


@app.route('/', methods=['GET'])
def home():
    """Redirect to dashboard"""
    from flask import redirect
    return redirect('/dashboard')


@app.route('/healthcheck', methods=['GET'])
@require_api_key
def healthcheck():
    """Health check endpoint"""
    return jsonify({"result": "success"}), 200


@app.route('/tick/<trade_id>', methods=['POST'])
@require_api_key
def tick(trade_id):
    """
    Process a tick with AI recommendations.
    
    Args:
        trade_id (str): Unique identifier for this trade (path parameter)
    """
    try:
        # Get the tick data from request
        tick_data = request.get_json(force=True)
        
        if not tick_data:
            return jsonify({"result": "failure", "error": "No data provided"}), 400
        
    except Exception as e:
        # Handle non-JSON data
        return jsonify({"result": "failure", "error": "Invalid JSON data"}), 400
    
    try:
        # Extract fields from tick data
        positions = tick_data.get('Positions')
        market_summary = tick_data.get('Market_Summary')
        market_history = tick_data.get('market_history')
        
        # Validate required fields - all three are required
        if not positions:
            return jsonify({"result": "failure", "error": "Missing Positions field"}), 400
        
        if not market_summary:
            return jsonify({"result": "failure", "error": "Missing Market_Summary field"}), 400
        
        if not market_history:
            return jsonify({"result": "failure", "error": "Missing market_history field"}), 400
        
        # Extract the most recent date from market_history
        day = None
        if market_history and len(market_history) > 0:
            # Get the most recent date
            day = market_history[-1].get('day', datetime.now().strftime('%Y-%m-%d'))
        else:
            day = datetime.now().strftime('%Y-%m-%d')
        
        # Update local positions from tick data
        save_positions(positions)
        
        # Prepare data for AI (normalize to expected format)
        normalized_data = {
            'POSITIONS': positions,
            'DAY': day,
            'Market_Summary': market_summary,
            'market_history': market_history
        }
        
        # Get AI recommendations and post to mothership
        recommendations, mothership_response = process_tick_with_ai(normalized_data, trade_id)
        
        # Check if mothership call was successful
        if "error" in mothership_response:
            # If mothership fails, we still continue with local processing
            print(f"Mothership error: {mothership_response['error']}")
            updated_positions = positions
        else:
            # Update positions from mothership response
            if "Positions" in mothership_response:
                updated_positions = mothership_response["Positions"]
                save_positions(updated_positions)
            else:
                updated_positions = positions
        
        # Calculate unrealized P&L
        unrealized_pnl = calculate_unrealized_pnl(positions, market_summary)
        
        # Log the trade
        trading_log = load_trading_log()
        log_entry = {
            "trade_id": trade_id,
            "timestamp": datetime.now().isoformat(),
            "day": day,
            "recommendations": recommendations,
            "positions_before": positions,
            "positions_after": updated_positions,
            "unrealized_pnl": unrealized_pnl,
            "mothership_response": mothership_response
        }
        trading_log.append(log_entry)
        save_trading_log(trading_log)
        
        # Return response in expected format
        return jsonify({
            "result": "success",
            "summary": {
                "unrealized_pnl": unrealized_pnl,
                "total_positions": len(positions),
                "day": day
            },
            "decisions": recommendations
        }), 200
    
    except Exception as e:
        print(f"Error in /tick: {e}")
        return jsonify({"result": "failure", "error": str(e)}), 500


@app.route('/dashboard', methods=['GET'])
def dashboard():
    """
    Display dashboard with positions, logs, and trading history.
    No authentication required.
    """
    try:
        positions = load_positions()
        trading_log = load_trading_log()
        
        # Fetch mothership positions
        mothership_positions = get_mothership_positions()
        
        # Simple HTML dashboard
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Trading Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
                h1 { color: #333; }
                h2 { color: #555; margin-top: 30px; }
                table { border-collapse: collapse; width: 100%; margin-top: 20px; background-color: white; }
                th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
                th { background-color: #4CAF50; color: white; }
                tr:nth-child(even) { background-color: #f9f9f9; }
                .section { margin-top: 30px; background-color: white; padding: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .info { background-color: #e3f2fd; padding: 10px; border-radius: 5px; margin-bottom: 20px; }
                .mothership-link { color: #1976d2; text-decoration: none; }
                .mothership-link:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <h1>🤖 Trading Dashboard</h1>
            
            <div class="info">
                <strong>Mothership Positions:</strong> 
                <a href="{{ mothership_url }}" target="_blank" class="mothership-link">
                    View Live Positions on Mothership →
                </a>
            </div>
            
            <div class="section">
                <h2>📊 Mothership Current Positions</h2>
                {% if mothership_positions.error %}
                    <p style="color: red;">Error fetching mothership positions: {{ mothership_positions.error }}</p>
                {% elif mothership_positions %}
                    <table>
                        <tr>
                            <th>Ticker</th>
                            <th>Quantity</th>
                            <th>Purchase Price</th>
                        </tr>
                        {% for pos in mothership_positions %}
                        <tr>
                            <td><strong>{{ pos.ticker }}</strong></td>
                            <td>{{ pos.quantity }}</td>
                            <td>${{ "%.2f"|format(pos.purchase_price) }}</td>
                        </tr>
                        {% endfor %}
                    </table>
                {% else %}
                    <p>No positions found on mothership.</p>
                {% endif %}
            </div>
            
            <div class="section">
                <h2>💼 Local Positions</h2>
                {% if positions %}
                <table>
                    <tr>
                        <th>Ticker</th>
                        <th>Quantity</th>
                        <th>Purchase Price</th>
                    </tr>
                    {% for pos in positions %}
                    <tr>
                        <td><strong>{{ pos.ticker }}</strong></td>
                        <td>{{ pos.quantity }}</td>
                        <td>${{ "%.2f"|format(pos.purchase_price) }}</td>
                    </tr>
                    {% endfor %}
                </table>
                {% else %}
                    <p>No local positions recorded yet.</p>
                {% endif %}
            </div>
            
            <div class="section">
                <h2>📝 Recent Trading Log</h2>
                {% if trading_log %}
                <table>
                    <tr>
                        <th>Timestamp</th>
                        <th>Trade ID</th>
                        <th>Day</th>
                        <th>P&L</th>
                        <th>Decisions</th>
                    </tr>
                    {% for log in trading_log[-10:] %}
                    <tr>
                        <td>{{ log.timestamp }}</td>
                        <td>{{ log.trade_id }}</td>
                        <td>{{ log.day }}</td>
                        <td>${{ "%.2f"|format(log.unrealized_pnl) if log.unrealized_pnl else "N/A" }}</td>
                        <td>{{ log.recommendations|length }} trades</td>
                    </tr>
                    {% endfor %}
                </table>
                {% else %}
                    <p>No trading activity recorded yet.</p>
                {% endif %}
            </div>
        </body>
        </html>
        """
        
        mothership_url = os.getenv("MOTHERSHIP_POSITIONS_URL", "https://mothership-crg7hzedd6ckfegv.eastus-01.azurewebsites.net/positions")
        
        return render_template_string(
            html, 
            positions=positions, 
            trading_log=trading_log,
            mothership_positions=mothership_positions if not isinstance(mothership_positions, dict) or 'error' not in mothership_positions else [],
            mothership_url=mothership_url
        ), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)