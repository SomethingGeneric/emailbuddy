import imaplib
import email
import time
import sys
import signal
import getpass
import openai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Connect to the IMAP server
mail = imaplib.IMAP4_SSL("sop.al")

sender_addr = input("Email: ")
sender_passw = getpass.getpass()

mail.login(sender_addr, sender_passw)
mail.select("inbox")

openai.api_key = open(".key").read().strip()

start_messages = [
    {
        "role": "system",
        "content": "You are responding to a short form message from a user. It could be about anything",
    },
]


# Define a function to retrieve the latest unread email
def get_latest_email():
    _, messages = mail.search(None, "UNSEEN")
    if messages[0] == b"":
        return None
    else:
        latest_message_id = messages[0].split()[-1]
        _, message_data = mail.fetch(latest_message_id, "(RFC822)")
        message_text = message_data[0][1].decode()
        message = email.message_from_string(message_text)
        return message


# Define a function to extract the email body and sender from a message
def get_email_details(message):
    body = ""
    sender = ""
    for part in message.walk():
        if part.get_content_type() == "text/plain":
            body = part.get_payload(decode=True).decode()
    sender = message["From"]
    return body, sender


# Define a function to generate a response using the local model
def generate_response(prompt):
    my_msgs = start_messages.copy()
    my_msgs.append({"role": "user", "content": prompt})
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=my_msgs,
    )
    return response["choices"][0]["message"]["content"]


# Define a function to handle SIGTERM signal
def sigterm_handler(signal, frame):
    print("SIGTERM received. Exiting...")
    sys.exit(0)


# Set up the SIGTERM signal handler
signal.signal(signal.SIGTERM, sigterm_handler)

# Retrieve the latest unread email
message = get_latest_email()

# Run the daemon loop
while True:
    try:
        print("Checking for emails")

        # Retrieve the latest unread email
        message = get_latest_email()

        # If there is an unread email and it's not from the bot, extract the details and generate a response
        if message and message["From"] != "me":
            print("Found a new message")
            body, sender = get_email_details(message)
            response = generate_response(body)

            from_email = sender_addr
            to_email = sender
            subject = "Re: {}".format(message["Subject"])
            body = response

            msg = MIMEMultipart()
            msg["From"] = from_email
            msg["To"] = to_email
            #msg["Subject"] = subject

            msg.attach(MIMEText(body, "plain"))

            smtp_server = sender_addr.split("@")[1]
            smtp_port = 587
            smtp_username = sender_addr
            smtp_password = sender_passw

            with smtplib.SMTP(smtp_server, smtp_port) as smtp:
                smtp.starttls()
                smtp.login(smtp_username, smtp_password)
                smtp.send_message(msg)

        # Wait for 10 seconds before checking for new emails again
        print("Sleeping before next check.")
        time.sleep(10)

    except KeyboardInterrupt:
        print("Keyboard interrupt received. Exiting...")
        sys.exit(0)

    except Exception as e:
        print("An error occurred:", e)
