from flask import Flask, jsonify, request
import requests
import mysql.connector
import json

app = Flask(__name__)

# Database Configuration
DB_CONFIG = {
    "host": "localhost",
    "user": "admin_elaa",
    "password": "admin_elaa_password123",
    "database": "sakila",
}


# Utility function to establish a database connection
def get_db_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as err:
        raise ConnectionError(f"Database connection failed: {err}")


# Utility function to load instance details
def get_instance_details():
    try:
        with open("instance_info.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        raise FileNotFoundError("Instance details file not found")
    except json.JSONDecodeError:
        raise ValueError("Error decoding JSON from instance details file")


# Health Check Endpoint
@app.route("/health", methods=["GET"])
def health_check():
    try:
        connection = get_db_connection()
        if connection.is_connected():
            connection.close()
            return jsonify({"status": "healthy"}), 200
    except ConnectionError as err:
        return jsonify({"status": "unhealthy", "error": str(err)}), 500


# Execute a Read Query Endpoint
@app.route("/read", methods=["POST"])
def read_data():
    data = request.json
    query = data.get("query")
    if not query:
        return jsonify({"error": "Query is missing"}), 400

    print("Read query:", query)

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query)
        rows = cursor.fetchall()
        connection.close()
        return jsonify({"data": rows}), 200
    except ConnectionError as err:
        return jsonify({"error": str(err)}), 500
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500


# Execute a Write Query Endpoint
@app.route("/write", methods=["POST"])
def write_data():
    data = request.json
    query = data.get("query")
    if not query:
        return jsonify({"error": "Query is missing"}), 400

    print("Write Query:", query)

    try:
        instance_details = get_instance_details()
    except (FileNotFoundError, ValueError) as e:
        return jsonify({"error": str(e)}), 500

    # Separate instance IDs and public IPs for forwarding
    instance_ids = [instance["InstanceID"] for instance in instance_details if instance["Name"] != "mysql_master_node"]
    public_ips = [instance["PublicIP"] for instance in instance_details if instance["Name"] != "mysql_master_node"]

    responses = []

    # Execute query locally
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(query)
        connection.commit()
        affected_rows = cursor.rowcount
        connection.close()

        local_response = {
            "message": "Query executed successfully",
            "affected_rows": affected_rows
        }
    except ConnectionError as err:
        local_response = {"message": "Query failed", "error": str(err), "affected_rows": 0}
    except mysql.connector.Error as err:
        local_response = {"message": "Query failed", "error": str(err), "affected_rows": 0}

    responses.append(local_response)

    # Forward query to other servers
    for ip in public_ips:
        try:
            url = f"http://{ip}:80/write"
            print("Write replay URL:", url)
            response = requests.post(url, json={"query": query})
            if response.status_code == 200:
                json_response = response.json()
                responses.append({
                    "message": json_response.get("message", "No message provided"),
                    "affected_rows": json_response.get("affected_rows", 0)
                })
            else:
                responses.append({
                    "message": "Query forwarding failed",
                    "error": response.json(),
                    "affected_rows": 0
                })
        except requests.RequestException as e:
            responses.append({
                "message": "Query forwarding failed",
                "error": str(e),
                "affected_rows": 0
            })

    return jsonify(responses), 200


if __name__ == "__main__":
    port = 80
    app.run(host="0.0.0.0", port=port)
