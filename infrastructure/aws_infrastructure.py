import boto3
import time
from config import (
    AVAILABILITY_ZONE,
    SECRET_KEY_NAME,
    MYSQL_NODE_TYPE,
    PROXY_MANAGER_NODE_TYPE,
    GATEKEEPER_NODE_TYPE,
    TRUSTED_HOST_NODE_TYPE,
    MYSQL_NODE_COUNT,
    PROXY_MANAGER_NODE_COUNT,
    GATEKEEPER_NODE_COUNT,
    TRUSTED_HOST_NODE_COUNT
)
from aws_infrastructure_utilities import (
    create_keypair,
    get_local_ip_cidr,
    create_vpc_and_subnet,
    create_security_groups,
    get_latest_ubuntu_ami,
    create_instances,
    collect_instance_data,
    save_instance_details
)

from aws_remote_app_deployment import (
    deploy_master,
    deploy_slave,
    deploy_proxy_manager,
    deploy_gatekeeper,
    deploy_trusted_host
)


def main():
    """
    Main function to set up the infrastructure, launch instances, and deploy applications.
    """
    # Initialize EC2 resource and client for AWS operations
    ec2 = boto3.resource('ec2', region_name= AVAILABILITY_ZONE)
    ec2_client = boto3.client('ec2', region_name= AVAILABILITY_ZONE)

    # Step 1: Create a key pair for SSH access
    key_pair = create_keypair(ec2_client, SECRET_KEY_NAME)

    # Step 2: Get the CIDR for the local machine's IP
    local_ip_cidr = get_local_ip_cidr()

    # Step 3: Set up VPC, subnet, and security groups
    vpc_id, subnet = create_vpc_and_subnet(ec2_client, ec2)
    gatekeeper_sg, trusted_host_sg, proxy_manager_sg, mysql_sg = create_security_groups(
        ec2_client, vpc_id, local_ip_cidr
    )

    # Step 4: Get the latest Ubuntu AMI ID
    ubuntu_ami_id = get_latest_ubuntu_ami(ec2_client)

    # Step 5: Launch EC2 instances for various roles
    mysql_instances = create_instances(
        ec2, ubuntu_ami_id, MYSQL_NODE_TYPE, MYSQL_NODE_COUNT,
        subnet, mysql_sg, 'MySQLNodes', key_pair
    )
    proxy_manager_instances = create_instances(
        ec2, ubuntu_ami_id, PROXY_MANAGER_NODE_TYPE, PROXY_MANAGER_NODE_COUNT,
        subnet, proxy_manager_sg, 'ProxyManagerNode', key_pair
    )
    trusted_host_instances = create_instances(
        ec2, ubuntu_ami_id, TRUSTED_HOST_NODE_TYPE, TRUSTED_HOST_NODE_COUNT,
        subnet, trusted_host_sg, 'TrustedHostNode', key_pair
    )
    gatekeeper_instances = create_instances(
        ec2, ubuntu_ami_id, GATEKEEPER_NODE_TYPE, GATEKEEPER_NODE_COUNT,
        subnet, gatekeeper_sg, 'GateKeeperNode', key_pair
    )

    # Allow instances some time to start up
    time.sleep(60)

    # Step 6: Collect instance data and tag them appropriately
    mysql_instance_data = collect_instance_data(mysql_instances, 'mysql_master_node', 'mysql_slave_node')
    proxy_manager_data = collect_instance_data(proxy_manager_instances, 'proxy_manager_node')
    gatekeeper_data = collect_instance_data(gatekeeper_instances, 'gatekeeper_node')
    trusted_host_data = collect_instance_data(trusted_host_instances, 'trusted_host_node')

    # Step 7: Save instance details to JSON files
    save_instance_details(mysql_instance_data, proxy_manager_data, gatekeeper_data, trusted_host_data)

    # Step 8: Deploy applications to the instances
    deploy_master()
    deploy_slave()
    deploy_proxy_manager()
    deploy_gatekeeper()
    deploy_trusted_host()




if __name__ == "__main__":
    main()
