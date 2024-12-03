# AWS MySQL DB Cluster with Proxy and Gatekeeper Patterns

This is the final project assignment for the cloud computing course on fall 2024 at polytechnique Montreal.


## Project Overview

This project implements a MySQL database cluster on AWS EC2 instances, utilizing Proxy and Gatekeeper cloud design patterns. The setup emphasizes scalability, security, and performance using automated scripts and benchmarking tools.


##Features

- MySQL Cluster:
Configured with three nodes: one manager and two workers.
Manager node handles write operations.
Worker nodes handle read operations.
Integrated with the Sakila database.

- Proxy Pattern:
Implements routing strategies for database requests:
Direct Hit: Routes all requests to the manager node.
Random Selection: Routes requests randomly to worker nodes.
Customized: Routes requests to the worker node with the lowest latency.

- Gatekeeper Pattern:
Gatekeeper: Internet-facing instance for request validation.
Trusted Host: Processes validated requests internally.



## How to Run

Clone the repository:
https://github.com/elaamokhtari/AWS-MySQL-DB-Cluster-with-Proxy-and-Gatekeeper-Patterns.git

Navigate to the project directory:
cd AWS-MySQL-DB-Cluster-with-Proxy-and-Gatekeeper-Patterns

Run the script:
./start.sh 
