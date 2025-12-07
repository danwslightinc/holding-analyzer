import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from dotenv import load_dotenv

# Import main to generate the dashboard
# We need to make sure main.py generates the file 'portfolio_dashboard.html'
from main import main as run_stock_analysis

# Load environment variables
load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

if not SENDER_EMAIL or not SENDER_PASSWORD or not RECIPIENT_EMAIL:
    print("Error: Please set SENDER_EMAIL, SENDER_PASSWORD, and RECIPIENT_EMAIL in .env file.")
    sys.exit(1)

def send_email():
    print("Generating latest analysis...")
    summary_text = run_stock_analysis()
    
    file_path = "portfolio_dashboard.html"
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found. Analysis might have failed.")
        return

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = f"Weekly Stock Portfolio Dashboard - {datetime.now().strftime('%Y-%m-%d')}"

    # HTML Body with embedded image CID
    html_body = "<html><body>"
    html_body += "<p>Here is your weekly stock portfolio analysis dashboard. <b>Open the attached HTML file for the interactive version.</b></p>"
    
    if summary_text:
        # Convert text summary to simple HTML
        summary_html = summary_text.replace("\n", "<br>")
        html_body += f"<pre>--- Weekly Highlights ---<br>{summary_html}</pre>"

    # Add the Image
    html_body += '<br><img src="cid:dashboard_image"><br>'
    html_body += "</body></html>"

    msg.attach(MIMEText(html_body, 'html'))
    
    # 1. Attach Inline Image
    img_path = "dashboard_preview.png"
    if os.path.exists(img_path):
        try:
            with open(img_path, 'rb') as f:
                img_data = f.read()
            image = MIMEBase('image', 'png')
            image.set_payload(img_data)
            encoders.encode_base64(image)
            image.add_header('Content-ID', '<dashboard_image>')
            image.add_header('Content-Disposition', 'inline', filename='dashboard_preview.png')
            msg.attach(image)
        except Exception as e:
            print(f"Error embedding image: {e}")

    # 2. Attach Interactive HTML (as file)
    try:
        with open(file_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {file_path}",
        )
        msg.attach(part)
    except Exception as e:
        print(f"Error attaching file: {e}")
        return

    # Send
    print(f"Sending email to {RECIPIENT_EMAIL}...")
    try:
        # Assuming Gmail for now, but could be configured
        # standard port 587 for TLS
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, text)
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")
        print("Tip: If using Gmail, ensure you are using an App Password, not your regular login password.")

if __name__ == "__main__":
    send_email()
