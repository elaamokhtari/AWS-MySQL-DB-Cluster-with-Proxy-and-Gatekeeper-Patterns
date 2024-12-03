import json
import requests
import time
from statistics import mean, stdev

# Authentication credentials
USERNAME = "admin_elaa"
PASSWORD = "admin_elaa_password123"

# Function to generate unique INSERT, UPDATE, and SELECT queries for the sakila database

def generate_sakila_queries():
    queries = {
        "INSERT": [
            f"INSERT INTO customer (store_id, first_name, last_name, email, address_id, create_date, last_update) VALUES (1, 'Customer{i}', 'Lastname{i}', 'customer{i}@example.com', {i % 10 + 1}, NOW(), NOW());"
            for i in range(100)
        ],
        "UPDATE": [
            f"UPDATE customer SET last_name = 'UpdatedLastname{i}' WHERE first_name = 'Customer{i}';"
            for i in range(100)
        ],
        "SELECT": [
            f"SELECT * FROM customer WHERE customer_id = {i + 1};" for i in range(100)
        ],
    }
    return queries

# Function to send requests to the Flask app and measure response times
def send_requests_to_api(queries, mode, repetitions):
    with open('gatekeeper_info.json', 'r') as file:
        instance_details = json.load(file)

    public_ips = [instance['PublicIP'] for instance in instance_details]
    base_url = f"http://{public_ips[0]}:80/process"

    headers = {
        "username": USERNAME,
        "password": PASSWORD
    }
    response_times = []

    for _ in range(repetitions):
        for query in queries:
            print(f"Executing Query: {query}")
            payload = {"query": query, "mode": mode}
            try:
                start_time = time.time()
                response = requests.post(base_url, json=payload, headers=headers)
                end_time = time.time()
                response_times.append(end_time - start_time)

                if response.status_code != 200:
                    print(f"Error ({mode}): {response.status_code}, {response.json()}")
                else:
                    print(f"Response: {response.json()}")
            except requests.RequestException as e:
                print(f"Request failed ({mode}): {e}")

    # Calculate and display statistics
    avg_time = mean(response_times)
    min_time = min(response_times)
    max_time = max(response_times)
    std_dev = stdev(response_times) if len(response_times) > 1 else 0

    statistics = (
        f"Statistics for {mode} mode:\n"
        f"  Total queries executed: {len(queries) * repetitions}\n"
        f"  Average response time: {avg_time:.4f} seconds\n"
        f"  Minimum response time: {min_time:.4f} seconds\n"
        f"  Maximum response time: {max_time:.4f} seconds\n"
        f"  Standard deviation: {std_dev:.4f} seconds\n"
        f"{'=' * 50}\n"
    )

    # Print the statistics to the console
    print(statistics)

    # Save the statistics to a file
    with open("query_statistics.txt", "a") as file:
        file.write(statistics)

if __name__ == "__main__":
    repetitions = 10
    queries = generate_sakila_queries()

    # Run queries in DIRECT mode (mix of INSERT and UPDATE)
    print("Running queries in DIRECT mode...")
    send_requests_to_api(queries["INSERT"] + queries["UPDATE"], "DIRECT", repetitions)

    # Run queries in RANDOM mode (SELECT queries)
    print("Running queries in RANDOM mode...")
    send_requests_to_api(queries["SELECT"], "RANDOM", repetitions)

    # Run queries in CUSTOMIZED mode (SELECT queries)
    print("Running queries in CUSTOMIZED mode...")
    send_requests_to_api(queries["SELECT"], "CUSTOMIZED", repetitions)
