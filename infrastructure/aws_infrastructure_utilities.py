import json
import boto3
import os.path
import ipaddress
import requests
from config import VPC_CIDR_BLOCK, PUBLIC_CIDR_BLOCK, IG_DEST_CIDR_BLOCK

iam_client = boto3.client('iam')


# Create VPC, Subnet, and Route Table
def create_vpc_and_subnet(ec2_client, ec2_resource):
    try:
        # Create VPC
        vpc_response = ec2_client.create_vpc(CidrBlock=VPC_CIDR_BLOCK)
        vpc_id = vpc_response['Vpc']['VpcId']
        ec2_client.create_tags(Resources=[vpc_id], Tags=[{"Key": "Name", "Value": "LOG8415_LAB3"}])

        # Enable DNS support and DNS hostname
        ec2_client.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={'Value': True})
        ec2_client.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={'Value': True})

        vpc = ec2_resource.Vpc(vpc_id)
        vpc.wait_until_available()

        # Create Subnet
        subnet = ec2_resource.create_subnet(VpcId=vpc.id, CidrBlock=PUBLIC_CIDR_BLOCK)

        # Create and attach IGW to VPC
        ig = ec2_resource.create_internet_gateway()
        vpc.attach_internet_gateway(InternetGatewayId=ig.id)

        # Create Route Table and associate it
        route_table = vpc.create_route_table()
        route_table.create_route(DestinationCidrBlock=IG_DEST_CIDR_BLOCK, GatewayId=ig.id)
        route_table.associate_with_subnet(SubnetId=subnet.id)

        print("Created VPC and Subnet successfully.")
        return vpc_id, subnet

    except Exception as e:
        print(f"Error creating VPC and Subnet: {e}")
        return None, None, None



# Create Security Groups
def create_security_groups(ec2_client, vpc_id, ssh_allowed_ip):
    try:
        security_groups = {}

        # Create security groups
        groups_to_create = [
            ('gatekeeper', 'Internet-facing security group'),
            ('trusted_host', 'Trusted host security group'),
            ('proxy_manager', 'Proxy manager security group'),
            ('mysql_nodes', 'MySQL nodes security group')
        ]

        for name, description in groups_to_create:
            sg = ec2_client.create_security_group(
                GroupName=f'{name.upper()}_SG',
                Description=description,
                VpcId=vpc_id
            )
            security_groups[name] = sg['GroupId']
            print(f"Created {name} security group: {sg['GroupId']}")

        # Define Ingress and Egress rules for all security groups
        sg_rules = {
            'gatekeeper': [
                {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': ssh_allowed_ip}]},
                {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp', 'FromPort': 443, 'ToPort': 443, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'icmp', 'FromPort': -1, 'ToPort': -1, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ],
            'trusted_host': [
                {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': ssh_allowed_ip}]},
                {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp', 'FromPort': 443, 'ToPort': 443, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'icmp', 'FromPort': -1, 'ToPort': -1, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ],
            'proxy_manager': [
                {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': ssh_allowed_ip}]},
                {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp', 'FromPort': 443, 'ToPort': 443, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'icmp', 'FromPort': -1, 'ToPort': -1, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ],
            'mysql_nodes': [
                {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': ssh_allowed_ip}]},
                {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp', 'FromPort': 443, 'ToPort': 443, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'icmp', 'FromPort': -1, 'ToPort': -1, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ]
        }

        # Authorize Ingress and Egress rules
        for sg_name, rules in sg_rules.items():
            sg_id = security_groups[sg_name]
            for rule in rules:
                ec2_client.authorize_security_group_ingress(GroupId=sg_id, IpPermissions=[rule])
                print(f"Configured ingress rule for {sg_name}")

        print("Security groups and rules configured successfully.")
        return security_groups ['gatekeeper'], security_groups ['trusted_host'], security_groups ['proxy_manager'], security_groups ['mysql_nodes'] 

    except Exception as e:
        print(f"Error creating security groups: {e}")
        return None



# Create Key Pair
def create_keypair(ec2_client, key_name):
    """
    Ensure a key pair with the specified name exists. 
    If it doesn't, create it and save the private key with secure permissions.
    """
    try:
        # Check if the key pair already exists
        key_pairs = ec2_client.describe_key_pairs(KeyNames=[key_name])
        if key_pairs and key_pairs.get('KeyPairs'):
            key_pair_id = key_pairs['KeyPairs'][0]['KeyName']
            print(f'Key pair "{key_pair_id}" already exists.')
            return key_pair_id

    except ec2_client.exceptions.ClientError as e:
        # Handle the case where the key pair doesn't exist (ClientError: InvalidKeyPair.NotFound)
        if 'InvalidKeyPair.NotFound' in str(e):
            print(f'Key pair "{key_name}" does not exist, creating a new one.')
        else:
            print(f'An error occurred: {e}')
            return None

    # Create the key pair since it doesn't exist
    try:
        key_pair = ec2_client.create_key_pair(KeyName=key_name, KeyType='rsa', KeyFormat='pem')
        private_key = key_pair.get('KeyMaterial')

        # Save the private key to a file
        key_file_path = f'{key_name}.pem'
        with open(key_file_path, 'w') as file:
            file.write(private_key)
        
        # Set file permissions to read-only for the owner (400)
        os.chmod(key_file_path, 0o400)

        key_pair_id = key_pair.get('KeyName')
        print(f'Key pair "{key_pair_id}" created and saved to {key_file_path}')
        return key_pair_id

    except Exception as e:
        print(f'Failed to create key pair: {e}')
        return None
    


# Get latest Ubuntu AMI
def get_latest_ubuntu_ami(ec2_client):
    images = ec2_client.describe_images(
        Filters=[
            {'Name': 'name', 'Values': ['ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*']},
            {'Name': 'architecture', 'Values': ['x86_64']},
            {'Name': 'root-device-type', 'Values': ['ebs']}
        ],
        Owners=['099720109477']
    )

    images = sorted(images['Images'], key=lambda x: x['CreationDate'], reverse=True)
    latest_ubuntu_ami = images[0]['ImageId'] if images else None
    if latest_ubuntu_ami:
        print(f"Latest Ubuntu AMI ID: {latest_ubuntu_ami}")
    else:
        print("No Ubuntu AMI found")
        exit(1)
    return latest_ubuntu_ami




# Get AWS credentials
def get_aws_credentials(profile='default'):
    credentials_path = os.path.expanduser('~/.aws/credentials')
    credentials = {}

    if not os.path.exists(credentials_path):
        raise FileNotFoundError(f"Credentials file not found at {credentials_path}")

    with open(credentials_path, 'r') as file:
        current_profile = None
        for line in file:
            line = line.strip()  # Strip newline and surrounding whitespace

            # Skip empty lines and comments
            if not line or line.startswith('#') or line.startswith(';'):
                continue

            # Check for profile section headers
            if line.startswith('[') and line.endswith(']'):
                current_profile = line[1:-1].strip()
                continue

            # Only process lines if in the correct profile
            if current_profile == profile:
                # Split only on the first '=' to handle values with '='
                key_value = line.split('=', 1)
                if len(key_value) == 2:
                    key, value = key_value[0].strip(), key_value[1].strip()
                    credentials[key] = value

    if not credentials:
        raise ValueError(f"No credentials found for profile: {profile}")

    return credentials



# Create EC2 instances
def create_instances(ec2,latest_ubuntu_ami, instance_type, count, subnet, sg_id, name_tag, keyname):
    print (f"Creating instance(s) for group {name_tag} ...")
    return ec2.create_instances(
        ImageId=latest_ubuntu_ami,  #  Amazon Machine Image (AMI) ID
        InstanceType=instance_type,
        KeyName=keyname,
        MaxCount=count,
        MinCount=count,
        NetworkInterfaces=[{
            'SubnetId': subnet.id,
            'DeviceIndex': 0,
            'AssociatePublicIpAddress': True,
            'Groups': [sg_id]
        }],
        BlockDeviceMappings=[{
            'DeviceName': '/dev/sda1',  # Adjust according to your AMI
            'Ebs': {
                'VolumeSize': 32,  # Size in GB
                'DeleteOnTermination': True,
                'VolumeType': 'gp2',  # General Purpose SSD
            }
        }],

        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [{'Key': 'Name', 'Value': f'Flask-{name_tag}'}]
        }]
    )



# Wait for instances to be in running state
def wait_for_instances(ec2_client, instance_ids):
    print("Waiting for instances to be in running state...")
    waiter = ec2_client.get_waiter('instance_running')
    waiter.wait(InstanceIds=instance_ids)
    print("Instances are now running.")



# Collect and tag instance data
def collect_instance_data(instances, master_name, slave_name=None):
    """
    Collects and tags instance data for master and optionally slave nodes.

    :param instances: List of EC2 instance objects.
    :param master_name: Name to tag the master node.
    :param slave_name: Name to tag slave nodes (optional).
    :return: List of dictionaries containing instance details.
    """
    instance_data = []

    for i, instance in enumerate(instances, start=1):
        instance.wait_until_running()
        instance.load()

        # Assign names based on master/slave role
        instance_name = master_name if i == 1 else (slave_name or master_name)
        instance.create_tags(Tags=[{'Key': 'Name', 'Value': instance_name}])

        instance_info = {
            'Name': instance_name,
            'InstanceID': instance.id,
            'PublicDNS': instance.public_dns_name,
            'PublicIP': instance.public_ip_address
        }
        instance_data.append(instance_info)

    return instance_data

# Save data to JSON file
def save_json(data, filename):
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)


# Save instance details to JSON files
def save_instance_details(mysql_data, proxy_manager_data, gatekeeper_data, trusted_host_data):
    """
    Saves instance details to JSON files for later reference.

    :param mysql_data: Data for MySQL master and slave nodes.
    :param proxy_manager_data: Data for proxy manager node.
    :param gatekeeper_data: Data for gatekeeper node.
    :param trusted_host_data: Data for trusted host node.
    """
    save_json(mysql_data, "../mysql/master/instance_info.json")
    save_json(mysql_data, "../mysql/proxy_manager/instance_info.json")
    save_json(proxy_manager_data, "../mysql/trusted_host/proxy_info.json")
    save_json(trusted_host_data, "../mysql/gatekeeper/trustedhost_info.json")
    save_json(gatekeeper_data, "../benchmark/gatekeeper_info.json")
    print("Instance details have been saved to JSON files.")



# Terminate instances
def terminate_instances (ec2_client, instance_ids):
    response = ec2_client.terminate_instances (instance_ids)
    print(response)
    print("Instances are now terminated.")

# Fetch the local machine's public IP address and calculate its CIDR block
def get_local_ip_cidr ():
    response = requests.get('https://api.ipify.org')
    public_ip = response.text.strip()
    subnet_mask = '255.255.255.0'
    cidr_network = ipaddress.ip_network(f"{public_ip}/{subnet_mask}", strict=False)

    return str(cidr_network)
