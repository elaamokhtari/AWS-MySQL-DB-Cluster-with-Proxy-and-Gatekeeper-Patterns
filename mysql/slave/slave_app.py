from flask import Flask, jsonify, request
import mysql.connector

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
    """
    Establishes and returns a connection to the database.
    """
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as err:
        raise ConnectionError(f"Database connection failed: {err}")


# Health Check Endpoint
@app.route("/health", methods=["GET"])
def health_check():
    """
    Health check to verify database connectivity.
    """
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
    """
    Executes a read query and returns the results.
    """
    data = request.json
    query = data.get("query")

    if not query:
        return jsonify({"error": "Query is missing"}), 400

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
    """
    Executes a write query and returns the result.
    """
    data = request.json
    query = data.get("query")

    if not query:
        return jsonify({"error": "Query is missing"}), 400

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(query)
        connection.commit()
        affected_rows = cursor.rowcount
        connection.close()
        return jsonify({"message": "Query executed successfully", "affected_rows": affected_rows}), 200
    except ConnectionError as err:
        return jsonify({"error": str(err)}), 500
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500


if __name__ == "__main__":
    port = 80
    app.run(host="0.0.0.0", port=port)
