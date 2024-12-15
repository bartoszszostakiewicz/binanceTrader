import os
import socket
import subprocess
import sys
import requests
from globals import RESTART_COMMAND, SENDER_EMAIL, RECEIVER_EMAIL, SENDER_EMAIL_KEY
from logger import logger
from git import Repo
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from os import getenv


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

def get_ngrok_tunnel():
    """
    Fetches the current ngrok TCP tunnel address.

    Returns:
        str: The TCP tunnel address, e.g., "tcp://0.tcp.eu.ngrok.io:10605".
        None: If no TCP tunnel is active or an error occurs.
    """
    try:
        # Ngrok web interface URL (default)
        ngrok_api_url = "http://127.0.0.1:4040/api/tunnels"

        # Fetch tunnel details
        response = requests.get(ngrok_api_url)
        response.raise_for_status()
        tunnels = response.json().get("tunnels", [])

        # Find the TCP tunnel
        for tunnel in tunnels:
            if tunnel["proto"] == "tcp":
                return tunnel["public_url"]  # e.g., "tcp://0.tcp.eu.ngrok.io:10605"

        return None  # No TCP tunnel found
    except requests.RequestException as e:
        logger.info(f"Probably non active ngrok tunnel!")
        return "None active tcp tunnel"

def get_tag():
    repo = Repo()

    tag = None
    for t in repo.tags:
        if t.commit == repo.head.commit:
            tag = t.name
            break
    return tag

def update_and_reboot(target_version=None):
    """
    Updates the repository to the latest tag or a specific tag if provided, and restarts the application/system.

    :param target_version: Optional argument to switch to a specific tag. If not provided, switches to the latest tag.
    """
    global UPDATE
    try:
        repo_path = os.getcwd()
        repo = Repo(repo_path)

        if repo.is_dirty():
            logger.warning("The repository has uncommitted changes. Please commit or discard them before updating.")
            return

        logger.info("Fetching updates from the remote repository...")
        repo.remotes.origin.fetch()
        logger.info("Repository fetched successfully.")

        logger.info("Fetching the latest tags from the remote repository...")
        repo.remotes.origin.fetch(tags=True)
        logger.info("Tags fetched successfully.")

        if target_version:
            if target_version in [tag.name for tag in repo.tags]:
                repo.git.checkout(target_version)
                logger.info(f"Switched to the specified version: {target_version}.")
            else:
                logger.error(f"Specified version {target_version} not found in the repository.")
                return
        else:
            tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime, reverse=True)
            if not tags:
                logger.error("No tags available in the repository.")
                return
            latest_tag = tags[0]
            repo.git.checkout(latest_tag.name)
            logger.info(f"Switched to the latest version: {latest_tag.name}.")

        logger.info("Restarting the application...")

        subprocess.Popen(RESTART_COMMAND, close_fds=True)
        sys.exit(0)

    except Exception as e:
        logger.error(f"An error occurred during the update process: {e}")

def send_email(subject, body, to_email = getenv(RECEIVER_EMAIL)):

    msg = MIMEMultipart()
    msg['From'] = getenv(SENDER_EMAIL)
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(getenv(SENDER_EMAIL), getenv(SENDER_EMAIL_KEY))
        server.send_message(msg)
    except Exception as e:
        print(f"Failed to send email: {e}")
    finally:
        server.quit()