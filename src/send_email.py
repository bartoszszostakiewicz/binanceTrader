import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from os import getenv

def send_email(subject, body, to_email = getenv('RECEIVER_EMAIL')):

    msg = MIMEMultipart()
    msg['From'] = getenv('SENDER_EMAIL')
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(getenv('SENDER_EMAIL'), getenv('SENDER_EMAIL_KEY'))
        server.send_message(msg)  
    except Exception as e:
        print(f"Failed to send email: {e}")
    finally:
        server.quit() 