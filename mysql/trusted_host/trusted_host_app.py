from flask import Flask, jsonify, request
import logging
import re
import requests
import json

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

# Constants
ALLOWED_MODES = {"DIRECT", "RANDOM", "CUSTOMIZED"}
VALID_CREDENTIALS = {
    "admin_elaa": "admin_elaa_password123"
}


# Utility Functions
def validate_user_credentials(headers):
    """
    Authenticates the user based on the provided headers.
    """
    username = headers.get("username")
    password = headers.get("password")
    app.logger.debug(f"Authentication attempt by username: {username}")

    if not username or not password:
        app.logger.error("Authentication failed: Missing credentials")
        return False, "Missing 'username' or 'password' in headers."

    if username not in VALID_CREDENTIALS or VALID_CREDENTIALS[username] != password:
        app.logger.error("Authentication failed: Invalid username or password")
        return False, "Invalid username or password."

    return True, None


def load_proxy_manager_details():
    """
    Loads proxy manager details from a configuration file.
    """
    try:
        with open("proxy_info.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        app.logger.error("proxy_info.json not found")
        raise FileNotFoundError("proxy_info.json not found")
    except json.JSONDecodeError:
        app.logger.error("Error decoding JSON from proxy_info.json")
        raise ValueError("Error decoding JSON from proxy_info.json")


def forward_query(url, data):
    """
    Forwards the query to the specified URL and handles the response.
    """
    try:
        app.logger.info(f"Forwarding request to {url}")
        response = requests.post(url, json=data)
        if response.status_code == 200:
            app.logger.info("Query processed successfully")
            return response.json(), 200
        else:
            app.logger.error(f"Query execution failed: {response.text}")
            return {
                "message": "Query execution failed",
                "error": response.text,
                "affected_rows": 0
            }, response.status_code
    except requests.RequestException as e:
        app.logger.critical(f"Query forwarding failed: {str(e)}")
        return {
            "message": "Query forwarding failed",
            "error": str(e),
            "affected_rows": 0
        }, 500


# Endpoints
@app.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint to verify application status.
    """
    app.logger.info("Health check endpoint accessed")
    return jsonify({"status": "healthy"}), 200


@app.route("/process", methods=["POST"])
def process_query():
    """
    Processes a query request and forwards it to the proxy manager.
    """
    data = request.json
    app.logger.debug(f"Received request payload: {data}")

    # Validate request payload
    if "query" not in data or "mode" not in data:
        app.logger.warning("Missing required keys in request payload")
        return jsonify({"error": "Missing required keys. Required keys: 'query', 'mode'"}), 400

    mode = data.get("mode").upper()
    if mode not in ALLOWED_MODES:
        app.logger.warning(f"Invalid mode provided: {mode}")
        return jsonify({"error": f"Invalid mode. Allowed modes are: {', '.join(ALLOWED_MODES)}"}), 400

    # Authenticate user
    is_authenticated, auth_error = validate_user_credentials(request.headers)
    if not is_authenticated:
        return jsonify({"error": auth_error}), 401

    # Forward query to the proxy manager
    try:
        instance_details = load_proxy_manager_details()
        proxy_manager_ip = next((instance["PublicIP"] for instance in instance_details), None)

        if not proxy_manager_ip:
            app.logger.error("No proxy manager IP found in the configuration")
            return jsonify({"error": "No proxy manager IP found"}), 500

        url = f"http://{proxy_manager_ip}:80/process"
        return forward_query(url, data)

    except (FileNotFoundError, ValueError) as e:
        app.logger.error(str(e))
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.logger.info("Starting Flask application")
    app.run(host="0.0.0.0", port=80)
