from flask import Flask, request, jsonify
import logging
import os
import queue

# Flask app setup
app = Flask(__name__)
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Optional: Secret for verifying incoming requests (set this in ServiceNow)
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "default_secret")

# Queue for login events
login_event_queue = queue.Queue()

# Function to enqueue login events for processing
def enqueue_login_event(user, timestamp):
    """Add login event to queue."""
    login_event = {"user": user, "timestamp": timestamp}
    login_event_queue.put(login_event)
    logger.info(f"Enqueued login event for user: {user}")

# Route to handle login events
@app.route('/login-event', methods=['POST'])
def login_event():
    """Endpoint to receive login events."""
    if not request.is_json:
        logger.warning("Invalid request: Non-JSON data received.")
        return jsonify({"status": "error", "message": "Invalid request format"}), 400

    data = request.json
    logger.info(f"Received login event: {data}")

    # Verify shared secret
    secret = data.get("secret")
    if secret != WEBHOOK_SECRET:
        logger.warning("Unauthorized request: Invalid secret.")
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    # Extract user details
    user = data.get('user')
    timestamp = data.get('timestamp')

    if user and timestamp:
        # Put login event in queue for Ansible Wrangler to process
        enqueue_login_event(user, timestamp)
        return jsonify({"status": "success", "message": "Login event processed"}), 200
    else:
        logger.error("Missing required fields in payload.")
        return jsonify({"status": "error", "message": "Invalid payload"}), 400

if __name__ == "__main__":
    # Run the app on port 5001
    app.run(host="0.0.0.0", port=5001)
