import re


def extract_otp(email_message):
    """Pulls the 6-digit OTP code out of a captured test email's body."""
    match = re.search(r'\b(\d{6})\b', email_message.body)
    assert match, f"No 6-digit OTP found in email body: {email_message.body!r}"
    return match.group(1)
