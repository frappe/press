import frappe
import subprocess
import shlex

class Client:
    """
    A simple client for executing commands on remote servers via SSH.
    """
    def __init__(self, server_name):
        """
        Initialize the SSH client with a server name.
        
        Args:
            server_name (str): Name of the server document
        """
        self.server_name = server_name
        self.server = frappe.get_doc(
            "Bare Metal Host" if frappe.db.exists("Bare Metal Host", server_name) 
            else "Server", server_name
        )
        
    def execute(self, command, _raise=True):
        """
        Execute a command on the remote server via SSH.
        
        Args:
            command (str): The command to execute
            _raise (bool): Whether to raise an exception on error
            
        Returns:
            object: An object with stdout and stderr attributes
        """
        ssh_command = self._build_ssh_command(command)
        
        try:
            process = subprocess.run(
                ssh_command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                check=_raise
            )
            
            result = frappe._dict({
                "stdout": process.stdout.strip() if process.stdout else "",
                "stderr": process.stderr.strip() if process.stderr else "",
                "returncode": process.returncode
            })
            
            if _raise and process.returncode != 0:
                error_message = f"Error executing command on {self.server_name}: {result.stderr}"
                frappe.log_error(error_message, "SSH Client Error")
                frappe.throw(error_message)
                
            return result
            
        except subprocess.CalledProcessError as e:
            if _raise:
                error_message = f"Error executing command on {self.server_name}: {e}"
                frappe.log_error(error_message, "SSH Client Error")
                frappe.throw(error_message)
            return frappe._dict({
                "stdout": "",
                "stderr": str(e),
                "returncode": e.returncode
            })
            
    def _build_ssh_command(self, command):
        """
        Build the SSH command with appropriate options.
        
        Args:
            command (str): The command to execute
            
        Returns:
            str: The complete SSH command
        """
        # Escape the command for shell execution
        escaped_command = shlex.quote(command)
        
        # Build the SSH command
        ssh_command = f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
        
        # Add port if specified
        if hasattr(self.server, 'ssh_port') and self.server.ssh_port:
            ssh_command += f" -p {self.server.ssh_port}"
            
        # Add user and server IP
        user = self.server.ssh_user if hasattr(self.server, 'ssh_user') and self.server.ssh_user else "root"
        ssh_command += f" {user}@{self.server.ip} {escaped_command}"
        
        return ssh_command 