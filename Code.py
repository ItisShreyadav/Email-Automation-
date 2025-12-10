import os
import logging
import time
from dotenv import load_dotenv
from imap_tools import MailBox, AND
from smolagents import tool, ToolCallingAgent, CodeAgent
from smolagents.models import InferenceClientModel
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from requests.auth import HTTPBasicAuth

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# --- Set multiple possible API key environment variables for Together API ---
os.environ["EMAIL_USER"] = "YOUR_MAIL"
os.environ["EMAIL_PASS"] = "EMAIL_PASSS"
os.environ["MODEL_API_KEY"] = "ENTER-API -KEY"
os.environ["MODEL_API_BASE"] = "API-BASE"
os.environ["MODEL_NAME"] = "LLM-MODEL"

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
MODEL_API_KEY = os.getenv("MODEL_API_KEY")
API_KEY = os.getenv("API_KEY")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
MODEL_API_BASE = os.getenv("MODEL_API_BASE")
MODEL_NAME = os.getenv("MODEL_NAME")

logging.info(f"Loaded config: EMAIL_USER={EMAIL_USER}, MODEL_API_KEY={MODEL_API_KEY}, API_KEY={API_KEY}, TOGETHER_API_KEY={TOGETHER_API_KEY}, MODEL_API_BASE={MODEL_API_BASE}, MODEL_NAME={MODEL_NAME}")

if not (EMAIL_USER and EMAIL_PASS and (MODEL_API_KEY or API_KEY or TOGETHER_API_KEY) and MODEL_API_BASE and MODEL_NAME):
    raise EnvironmentError(
        "Please set EMAIL_USER, EMAIL_PASS, API key, MODEL_API_BASE, and MODEL_NAME in environment variables."
    )

# --- Initialize inference model -- pass api_key explicitly using one of the available environment vars ---
inference_model = InferenceClientModel(api_key=TOGETHER_API_KEY or API_KEY or MODEL_API_KEY)

# --- Define Tools ---
@tool
def fetch_support_emails(limit: int = 5) -> list[dict]:
    """
    Fetch the first 'limit' unread support emails containing keywords: help, issue, problem.
    Marks emails as read after fetching.

    Args:
        limit (int): Maximum number of emails to fetch.

    Returns:
        list[dict]: List of emails with keys 'from', 'subject', 'body'.
    """
    emails_to_reply = []
    try:
        with MailBox("imap.gmail.com").login(EMAIL_USER, EMAIL_PASS) as mailbox:
            count = 0
            for msg in mailbox.fetch(AND(seen=False)):
                content = msg.text or msg.subject
                if any(word in content.lower() for word in ["help", "issue", "problem"]):
                    mailbox.flag(msg.uid, "\\Seen", True)
                    emails_to_reply.append({
                        "from": msg.from_,
                        "subject": msg.subject,
                        "body": content
                    })
                    count += 1
                    if count >= limit:
                        break
    except Exception as e:
        logging.error(f"Error fetching emails: {e}")
    return emails_to_reply

@tool
def generate_email_reply(email_body: str) -> str:
    """
    Generate a polite reply to an incoming support email.

    Args:
        email_body (str): Incoming email content.

    Returns:
        str: AI-generated reply text.
    """
    prompt = f"You are a helpful support assistant. Respond politely and helpfully to the email:\n\n{email_body}"
    try:
        response = inference_model.generate(prompt)
        return response.strip()
    except Exception as e:
        logging.error(f"Error generating AI reply: {e}")
        return "Thank you for reaching out. We have received your email and will get back to you soon."

@tool
def send_email_tool(recipient: str, subject: str, body: str) -> None:
    """
    Send an email via Gmail SMTP with UTF-8 encoding.

    Args:
        recipient (str): Recipient email address.
        subject (str): Email subject.
        body (str): Email body content.

    Returns:
        None
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, recipient, msg.as_string())
            logging.info(f"Email sent to {recipient}")
    except Exception as e:
        logging.error(f"Error sending email: {e}")

# --- Individual ToolCalling Agents ---
fetch_agent = ToolCallingAgent(
    name="FetchAgent",
    model=inference_model,
    tools=[fetch_support_emails],
    description="Fetches unread support emails containing help keywords."
)

reply_agent = ToolCallingAgent(
    name="ReplyAgent",
    model=inference_model,
    tools=[generate_email_reply],
    description="Generates polite AI replies to support emails."
)

send_agent = ToolCallingAgent(
    name="SendAgent",
    model=inference_model,
    tools=[send_email_tool],
    description="Sends email replies via SMTP."
)

# --- Manager CodeAgent ---
manager_agent = CodeAgent(
    name="ManagerAgent",
    model=inference_model,
    tools=[],
    managed_agents=[fetch_agent, reply_agent, send_agent],
    description=(
        "Orchestrates fetching unread support emails, generating polite replies, "
        "and sending them, delegating tasks to specialist agents."
    ),
    verbosity_level=2,
    max_steps=8
)

# ---  custom prompt for clarity ---
custom_system_prompt = (
    "\nYou are a support manager agent."
    "\nAnalyze incoming support emails, delegate to appropriate agents or use tools directly."
    "\nUse Thought / Action / Observation reasoning format."
)
manager_agent.prompt_templates["system_prompt"] += custom_system_prompt

# --- Motive  ---
if __name__ == "__main__":
    logging.info("Starting CodeAgent Manager for Email Automation...")
    while True:
        try:
            task = (
                "Fetch the first 5 unread support emails, "
                "generate polite replies, and send them back to the users."
            )
            manager_agent.run(task)
        except Exception as e:
            logging.error(f"Error in CodeAgent loop: {e}")
        time.sleep(60)
