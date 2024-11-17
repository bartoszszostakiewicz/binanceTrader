import socket
import requests
from logger import logger

def get_private_ip():
    """
    Retrieves the private IP address of the current network interface used for outbound connections.

    Returns:
        str or None: The private IP address as a string, or None if it cannot be determined.
    """
    try:
        # Attempt to connect to an external server (this doesn't actually send data out)
        # This step is just used to determine the preferred outbound IP address.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))  # Google DNS IP for reference
            private_ip = s.getsockname()[0]  # Get the local IP address used for the connection
        return private_ip
    except Exception as e:
        logger.exception(f"Failed to retrieve private IP address: {e}")
        return None
    
def get_public_ip():
    """
    Retrieves the public IP address of the current network.

    Returns:
        str or None: The public IP address as a string, or None if the request fails.
    """
    try:
        response = requests.get("https://api.ipify.org?format=json")
        response.raise_for_status()  # Check if the request was successful
        ip = response.json().get("ip")
        return ip
    except requests.RequestException as e:
        # Handle any request-related errors and return None if the IP retrieval fails
        logger.exception(f"Failed to retrieve public IP address: {e}")
        return None
    
