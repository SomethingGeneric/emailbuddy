import imaplib
import email
import time
import sys
import signal
import getpass
from transformers import pipeline

# Connect to the IMAP server
mail = imaplib.IMAP4_SSL('sop.al')
mail.login(input("Email: "), getpass.getpass())
mail.select('inbox')

# Set up the local model using transformers pipeline
nlp = pipeline('text-generation', model='distilbert-base-uncased', device=0)

# Define a function to retrieve the latest unread email
def get_latest_email():
    _, messages = mail.search(None, 'UNSEEN')
    if messages[0] == b'':
        return None
    else:
        latest_message_id = messages[0].split()[-1]
        _, message_data = mail.fetch(latest_message_id, '(RFC822)')
        message_text = message_data[0][1].decode()
        message = email.message_from_string(message_text)
        return message

# Define a function to extract the email body and sender from a message
def get_email_details(message):
    body = ""
    sender = ""
    for part in message.walk():
        if part.get_content_type() == 'text/plain':
            body = part.get_payload(decode=True).decode()
    sender = message['From']
    return body, sender

# Define a function to generate a response using the local model
def generate_response(prompt):
    response = nlp(prompt, max_length=1024, do_sample=True, temperature=0.7)[0]['generated_text']
    return response.strip()

# Define a function to handle SIGTERM signal
def sigterm_handler(signal, frame):
    print('SIGTERM received. Exiting...')
    sys.exit(0)

# Set up the SIGTERM signal handler
signal.signal(signal.SIGTERM, sigterm_handler)

# Run the daemon loop
while True:
    try:
        # Retrieve the latest unread email
        message = get_latest_email()

        # If there is an unread email, extract the details and generate a response
        if message:
            body, sender = get_email_details(message)
            response = generate_response(body)

            # Send the response back to the sender
            mail.append('inbox', None, None, ('From: me\r\nTo: {}\r\nSubject: Re: {}\r\n\r\n{}'.format(sender, message['Subject'], response)).encode())

        # Wait for 10 seconds before checking for new emails again
        time.sleep(10)

    except KeyboardInterrupt:
        print('Keyboard interrupt received. Exiting...')
        sys.exit(0)

    except Exception as e:
        print('An error occurred:', e)
