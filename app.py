import os
import random
import smtplib
from datetime import datetime, timedelta, timezone

from email.message import EmailMessage

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS


load_dotenv()

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return jsonify({
        "success": True,
        "message": "Tracer Backend is running"
    })


SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


# Temporary in-memory storage
otp_storage = {}


def generate_otp():
    return str(random.randint(100000, 999999))


def send_otp_email(receiver_email, otp):
    message = EmailMessage()

    message["Subject"] = "Tracer - Password Reset Code"
    message["From"] = SMTP_EMAIL
    message["To"] = receiver_email

    message.set_content(
        f"""
Hello,

Your Tracer password reset code is:

{otp}

This code is valid for 5 minutes.

If you did not request a password reset, please ignore this email.

Regards,
Tracer Team
"""
    )

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(message)


@app.route("/send-otp", methods=["POST"])
def send_otp():
    data = request.get_json()

    if not data or "email" not in data:
        return jsonify({
            "success": False,
            "message": "Email is required",
        }), 400

    email = data["email"].strip().lower()

    if not email:
        return jsonify({
            "success": False,
            "message": "Email cannot be empty",
        }), 400

    otp = generate_otp()

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    otp_storage[email] = {
        "otp": otp,
        "expires_at": expires_at,
        "attempts": 0,
    }

    try:
        send_otp_email(email, otp)

        return jsonify({
            "success": True,
            "message": "OTP sent successfully",
        })

    except Exception as e:
        print("Email error:", e)

        return jsonify({
            "success": False,
            "message": "Failed to send OTP",
        }), 500


@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "Request data is required",
        }), 400

    email = data.get("email", "").strip().lower()
    otp = data.get("otp", "").strip()

    if not email or not otp:
        return jsonify({
            "success": False,
            "message": "Email and OTP are required",
        }), 400

    record = otp_storage.get(email)

    if record is None:
        return jsonify({
            "success": False,
            "message": "No active OTP found",
        }), 400

    # Check expiration
    if datetime.now(timezone.utc) > record["expires_at"]:
        del otp_storage[email]

        return jsonify({
            "success": False,
            "message": "OTP has expired",
        }), 400

    # Limit attempts
    if record["attempts"] >= 5:
        del otp_storage[email]

        return jsonify({
            "success": False,
            "message": "Too many attempts",
        }), 429

    if otp != record["otp"]:
        record["attempts"] += 1

        return jsonify({
            "success": False,
            "message": "Invalid OTP",
        }), 400

    # OTP is correct
    del otp_storage[email]

    return jsonify({
        "success": True,
        "message": "OTP verified successfully",
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)