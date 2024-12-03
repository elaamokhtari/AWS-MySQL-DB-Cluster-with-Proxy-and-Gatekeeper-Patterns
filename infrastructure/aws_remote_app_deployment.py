import paramiko
import os
import json
from config import SECRET_KEY_PATH
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# upload an entire directory to the remote server via SFTP
def upload_directory(ssh_client, local_directory):
    """
    Uploads an entire directory to the remote server via SFTP.

    :param ssh_client: The SSH client object.
    :param local_directory: The local directory to upload.
    """
    directory_map = {
        "master": "../mysql/master",
        "slave": "../mysql/slave",
        "proxy_manager": "../mysql/proxy_manager",
        "trusted_host": "../mysql/trusted_host",
        "gatekeeper": "../mysql/gatekeeper"
    }

    local_directory = directory_map.get(local_directory, "../mysql/gatekeeper")
    local_absolute_path = os.path.abspath(local_directory)
    
    # Start SFTP session
    sftp = ssh_client.open_sftp()
    
    print(f"Uploading files in {local_absolute_path}")

    try:
        for item in os.listdir(local_directory):
            local_path = os.path.join(local_absolute_path, item)
            remote_app_path = f"/home/ubuntu/{item}"
            print(f"Uploading {local_path} to {remote_app_path}")
            sftp.put(local_path, remote_app_path)
            print(f"Uploaded {local_path} to {remote_app_path}")

    finally:
        sftp.close()  # Close the SFTP session


def save_statistics_to_file(instance_name, instance_id, statistics_output):
    """
    Save only the desired sysbench statistics to a log file under the instance name.

    :param instance_name: The name of the instance.
    :param instance_id: The ID of the instance.
    :param statistics_output: The sysbench output statistics.
    """
    file_path = "sysbench_statistics.log"
    with open(file_path, "a") as file:
        file.write(f"Instance Name: {instance_name}, Instance ID: {instance_id}\n")
        file.write(statistics_output)
        file.write("\n" + "=" * 50 + "\n\n")

def extract_relevant_statistics(output):
    """
    Extract the relevant portion of sysbench statistics from the output.

    :param output: The full sysbench output.
    :return: The extracted relevant portion.
    """
    match = re.search(r"SQL statistics:.*?Threads fairness:.*?execution time \(avg/stddev\):.*?(?:\n|$)", output, re.DOTALL)
    if match:
        return match.group(0)
    else:
        return "Relevant statistics not found."

# Set up the deployment environment on the remote server
def setup_deployment(path, app_name, public_ip, instance_id, instance_name, is_db=True):
    install_commands = [
        'sudo apt-get update',
        'sudo apt install python3 python3-pip -y',
        'sudo pip3 install flask gunicorn requests boto3'
    ]

    if is_db:
        install_commands.append('sudo pip3 install mysql-connector-python')

    try:
        print(f"Connecting to {public_ip} for {instance_id} in {path}...")

        # Initialize SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(public_ip, username='ubuntu', key_filename=SECRET_KEY_PATH)

        print(f"Connected to {public_ip} for {instance_id} in {path}...")
        
        for install_command in install_commands:
            stdin, stdout, stderr = ssh.exec_command(install_command)
            stdout.channel.recv_exit_status()  # Wait for the command to finish
            print(f"Completed running {install_command} ...")    

        print(f"Completed running start commands for {public_ip} in {path}...")
        
        upload_directory(ssh, path)
        print(f"Completed uploading files for {public_ip} in {path}...")

        if is_db:
            stdin, stdout, stderr = ssh.exec_command('python3 sysbench_setup.py')
            stdout.channel.recv_exit_status()
            sysbench_output = stdout.read().decode()
            sysbench_errors = stderr.read().decode()

            if sysbench_errors:
                print(f"Sysbench errors for {instance_id}: {sysbench_errors}")

            # Extract only the relevant statistics
            relevant_statistics = extract_relevant_statistics(sysbench_output)

            # Print relevant statistics to the terminal
            print(f"Sysbench Statistics for {instance_id}:")
            print(relevant_statistics)

            # Save the output to the file
            save_statistics_to_file(instance_name, instance_id, relevant_statistics)

        app_deploy_cmd = f"sudo gunicorn {app_name.split('/')[-1].split('.')[0]}:app -w 4 --bind 0.0.0.0:80 --log-level debug --access-logfile access.log --error-logfile error.log &"
        stdin, stdout, stderr = ssh.exec_command(app_deploy_cmd)
        stdout.channel.recv_exit_status()
        print(f"Completed deploying {app_name} at {public_ip} in {path}...")
    
    except Exception as e:
        print(f"Error deploying to {public_ip}: {e}")
    finally:
        ssh.close()


# Deploy an instance
def deploy_instance(instance_file, name_filter, path, app_name, is_db=True):
    with open(instance_file, 'r') as file:
        instance_details = json.load(file)
    
    for instance in instance_details:
        if instance['Name'] == name_filter or name_filter == 'all':
            setup_deployment(path, app_name, instance['PublicIP'], instance['InstanceID'], instance['Name'], is_db)


# Deploy the master node
def deploy_master():
    deploy_instance('../mysql/master/instance_info.json', 'mysql_master_node', "master", "master_app.py", is_db=True)

# Deploy the slave node
def deploy_slave():
    deploy_instance('../mysql/master/instance_info.json', 'all', "slave", "slave_app.py", is_db=True)

# Deploy the proxy manager
def deploy_proxy_manager():
    deploy_instance('../mysql/trusted_host/proxy_info.json', 'all', "proxy_manager", "proxy_manager_app.py", is_db=False)

# Deploy the trusted host
def deploy_trusted_host():
    deploy_instance('../mysql/gatekeeper/trustedhost_info.json', 'all', "trusted_host", "trusted_host_app.py", is_db=False)

# Deploy the gatekeeper
def deploy_gatekeeper():
    deploy_instance('../benchmark/gatekeeper_info.json', 'all', "gatekeeper", "gatekeeper_app.py", is_db=False)

if __name__ == "__main__":
    deploy_trusted_host()
