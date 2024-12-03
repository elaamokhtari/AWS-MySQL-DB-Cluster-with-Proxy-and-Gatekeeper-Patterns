from flask import Flask, jsonify, request
import requests
import subprocess
import json
import random
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# Utility Functions
def load_instance_details():
    """
    Loads instance details from the configuration file.
    """
    try:
        with open("instance_info.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        logging.error("instance_info.json not found")
        raise FileNotFoundError("instance_info.json not found")
    except json.JSONDecodeError:
        logging.error("Error decoding JSON from instance_info.json")
        raise ValueError("Error decoding JSON from instance_info.json")


def ping_address(ip):
    """
    Pings an IP address and returns the average ping time in milliseconds.
    Returns None if the ping fails.
    """
    command = ["ping", "-c", "1", ip]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            output = result.stdout
            time_line = next(line for line in output.splitlines() if "time=" in line)
            time_ms = float(time_line.split("time=")[1].split()[0])
            return time_ms
        return None
    except Exception as e:
        logging.warning(f"Ping failed for IP {ip}: {e}")
        return None


def find_lowest_latency_instance(instance_details):
    """
    Finds the instance with the lowest ping.
    """
    lowest_ping = float("inf")
    best_instance = None

    for instance in instance_details:
        if instance["Name"] != "mysql_master_node":
            ip = instance["PublicIP"]
            ping_time = ping_address(ip)
            if ping_time is not None and ping_time < lowest_ping:
                lowest_ping = ping_time
                best_instance = instance

    if best_instance:
        return best_instance["InstanceID"], best_instance["PublicIP"]
    raise ValueError("No instance with a valid ping found")


def select_random_read_node(instance_details):
    """
    Finds a random read node IP.
    """
    read_nodes = [instance for instance in instance_details if instance["Name"] != "mysql_master_node"]
    if not read_nodes:
        raise ValueError("No read nodes found")

    selected_instance = random.choice(read_nodes)
    return selected_instance["InstanceID"], selected_instance["PublicIP"]


def fetch_master_node(instance_details):
    """
    Retrieves the master node ip from the list of instances.
    """
    master_node = next((instance for instance in instance_details if instance["Name"] == "mysql_master_node"), None)
    if not master_node:
        raise ValueError("No master node found")
    return master_node["InstanceID"], master_node["PublicIP"]


def forward_query_request(url, payload):
    """
    Makes an API call to the specified URL with the given payload.
    """
    logging.info(f"Redirecting to URL: {url}")
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return response.json()
        return {
            "message": "Query execution failed",
            "error": response.text,
            "affected_rows": 0,
        }
    except requests.RequestException as e:
        logging.error(f"API call failed: {e}")
        return {
            "message": "Query forwarding failed",
            "error": str(e),
            "affected_rows": 0,
        }


# Flask Endpoints
@app.route("/process", methods=["POST"])
def process_query():
    """
    Processes queries and forwards them based on mode (DIRECT, RANDOM, or CUSTOMIZED).
    """
    data = request.json
    query = data.get("query")
    mode = data.get("mode")
    if not query or not mode:
        return jsonify({"error": "Missing query or mode"}), 400

    try:
        instance_details = load_instance_details()

        # Mode-based routing logic
        if mode == "DIRECT":
            _, master_ip = fetch_master_node(instance_details)
            url = f"http://{master_ip}:80/write"
        elif mode == "RANDOM":
            _, random_ip = select_random_read_node(instance_details)
            url = f"http://{random_ip}:80/read"
        else:  # CUSTOMIZED or default mode
            _, lowest_ping_ip = find_lowest_latency_instance(instance_details)
            url = f"http://{lowest_ping_ip}:80/read"

        # Make the API call
        return jsonify(forward_query_request(url, {"query": query})), 200

    except (FileNotFoundError, ValueError) as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logging.exception("Unexpected error occurred")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint to verify the application status.
    """
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    logging.info("Starting Flask application")
    app.run(host="0.0.0.0", port=80)
