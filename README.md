# Email-Automation
We need to build a small email automation using SmolAgent.
•	Create a fake Gmail account for testing.
•	The system should use IMAP to fetch new emails from this account.
•	If the email looks like a customer support email (for example: contains words like help, issue, problem), then the system should automatically send a reply (like “Thank you, we’ll get back to you soon”).

Also added the .env file with all necessary credentials to access mail and sending replies

DETAILED OVERVIEW -----
Here we used our own model r1a1
-tools - fetch email, generate reply, send email
agents - to use the tools
main loop - check every 60 seconds for new emails, process first 5 unread emails

THROUGH THIS EXAMPLE I UNDERSTOOD THE EACH TOOL MORE NICELY ALONG WITH RUNNING IT LOCALLY AND UNDERSTANDING SMOLAGENTS
