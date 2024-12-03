import subprocess
import time


def run_shell_command(command, error_message="Error executing command", success_message="Command succeeded"):
    """
    Executes a shell command and prints the result.
    """
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
    if result.returncode != 0:
        print(f"{error_message}: {command}\n{result.stderr}")
    else:
        print(f"{success_message}: {command}\n{result.stdout}")


def install_mysql():
    """
    Installs MySQL server.
    """
    print("Installing MySQL Server...")
    run_shell_command("sudo apt update", "Failed to update system packages")
    run_shell_command("sudo apt install -y mysql-server", "Failed to install MySQL Server")


def configure_mysql():
    """
    Configures MySQL by creating a user, granting privileges, and creating a database.
    """
    print("Configuring MySQL...")
    commands = [
        "CREATE USER IF NOT EXISTS 'admin_elaa'@'localhost' IDENTIFIED WITH mysql_native_password BY 'admin_elaa_password123';",
        "GRANT ALL PRIVILEGES ON *.* TO 'admin_elaa'@'localhost';",
        "FLUSH PRIVILEGES;",
        "CREATE DATABASE IF NOT EXISTS sysbench_test;"
    ]
    for command in commands:
        run_shell_command(f"echo \"{command}\" | sudo mysql", f"Failed to execute: {command}")
    print("MySQL user and database configured successfully.")


def download_and_import_sakila():
    """
    Downloads and imports the Sakila database.
    """
    print("Downloading and importing Sakila database...")
    run_shell_command("wget https://downloads.mysql.com/docs/sakila-db.tar.gz", "Failed to download Sakila database")
    run_shell_command("tar -xvf sakila-db.tar.gz", "Failed to extract Sakila database")
    
    sakila_commands = [
        "mysql -u admin_elaa -p'admin_elaa_password123' sysbench_test < sakila-db/sakila-schema.sql",
        "mysql -u admin_elaa -p'admin_elaa_password123' sysbench_test < sakila-db/sakila-data.sql"
    ]
    for command in sakila_commands:
        run_shell_command(command, f"Failed to execute: {command}")

    print("Sakila database imported successfully.")


def run_sysbench():
    """
    Runs sysbench to benchmark the Sakila database.
    """
    print("Ensuring sysbench is installed...")
    run_shell_command("sudo apt update", "Failed to update system packages")
    run_shell_command("sudo apt install -y sysbench", "Failed to install sysbench")

    print("Running sysbench on Sakila database...")

    sysbench_commands = [
        "sysbench /usr/share/sysbench/oltp_read_write.lua "
        "--mysql-host=localhost --mysql-user=admin_elaa --mysql-password=admin_elaa_password123 "
        "--mysql-db=sakila --tables=4 --table-size=1000 prepare",
        "sysbench /usr/share/sysbench/oltp_read_write.lua "
        "--mysql-host=localhost --mysql-user=admin_elaa --mysql-password=admin_elaa_password123 "
        "--mysql-db=sakila --threads=8 --time=60 run",
        "sysbench /usr/share/sysbench/oltp_read_write.lua "
        "--mysql-host=localhost --mysql-user=admin_elaa --mysql-password=admin_elaa_password123 "
        "--mysql-db=sakila cleanup"
    ]

    for command in sysbench_commands:
        run_shell_command(command, f"Failed to execute: {command}")

    run_shell_command("touch mysql_setup_sysbench.success", "Failed to mark script success")
    print("Sysbench benchmark completed and cleaned up.")


def main():
    """
    Main function orchestrating the setup and benchmarking process.
    """
    install_mysql()
    time.sleep(10)  # Wait for MySQL installation to complete

    configure_mysql()
    time.sleep(5)  # Wait for MySQL to be ready

    download_and_import_sakila()
    run_sysbench()


if __name__ == "__main__":
    main()
