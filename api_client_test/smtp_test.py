import os
from datetime import datetime
import smtplib

EMAIL_HOST = os.environ.get("EMAIL_HOST", "test.mail.ru")
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "test@mail.ru")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "password")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "000"))

print(f"{EMAIL_HOST=}")
print(f"{EMAIL_HOST_USER=}")
print(f"{EMAIL_HOST_PASSWORD=}")
print(f"{EMAIL_PORT=}")

with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT) as s:

    s.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)

    s.sendmail(
        EMAIL_HOST_USER, "5845889@mail.ru", f"test smtp at: {str(datetime.now())[:19]}"
    )

print("END.")
