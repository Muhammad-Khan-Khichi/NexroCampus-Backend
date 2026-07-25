import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

# ============================================
# SEND EMAIL (Generic)
# ============================================

async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str = None
):
    """Send HTML email via SMTP"""
    
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        # DEV MODE: Print to console
        print(f"\n📧 ============ EMAIL (DEV MODE) ===========")
        print(f"📧 To: {to_email}")
        print(f"📧 Subject: {subject}")
        print(f"📧 Text Content:\n{text_content or html_content[:300]}...")
        print(f"📧 ==========================================\n")
        return True
    
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = settings.SMTP_FROM or settings.SMTP_USER
        msg['To'] = to_email
        msg['Subject'] = subject
        
        if text_content:
            part1 = MIMEText(text_content, 'plain')
            msg.attach(part1)
        
        part2 = MIMEText(html_content, 'html')
        msg.attach(part2)
        
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        
        return True
        
    except Exception as e:
        print(f"❌ Email send failed: {e}")
        return False


# ============================================
# SEND VERIFICATION EMAIL
# ============================================

async def send_verification_email(email: str, full_name: str, token: str):
    """Send beautiful email verification"""
    
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    
    subject = "Verify your NexroCampus account 🎓"
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background-color: #f3f4f6;
        }}
        .container {{
            max-width: 600px;
            margin: 40px auto;
            background: #ffffff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px 30px;
            text-align: center;
        }}
        .logo {{
            color: #ffffff;
            font-size: 32px;
            font-weight: bold;
            margin: 0;
        }}
        .content {{
            padding: 40px 30px;
        }}
        .greeting {{
            color: #1f2937;
            font-size: 24px;
            font-weight: 600;
            margin: 0 0 16px 0;
        }}
        .text {{
            color: #4b5563;
            font-size: 16px;
            line-height: 24px;
            margin: 16px 0;
        }}
        .button-container {{
            text-align: center;
            margin: 32px 0;
        }}
        .button {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #ffffff;
            text-decoration: none;
            padding: 14px 40px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 16px;
        }}
        .footer {{
            background: #f9fafb;
            padding: 24px 30px;
            text-align: center;
            border-top: 1px solid #e5e7eb;
        }}
        .footer-text {{
            color: #6b7280;
            font-size: 12px;
            margin: 4px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="logo">🎓 NexroCampus</h1>
        </div>
        <div class="content">
            <h2 class="greeting">Welcome, {full_name}! 👋</h2>
            <p class="text">
                Thanks for joining NexroCampus! To get started, please verify your email address.
            </p>
            <div class="button-container">
                <a href="{verification_url}" class="button">
                    ✉️ Verify Email Address
                </a>
            </div>
            <p class="text" style="text-align: center; color: #6b7280;">
                Or copy this link: {verification_url}
            </p>
        </div>
        <div class="footer">
            <p class="footer-text">© 2024 NexroCampus. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""
    
    text_content = f"""
Welcome to NexroCampus! 🎓

Hi {full_name},

Thanks for joining NexroCampus! To complete your registration, please verify your email:

{verification_url}

This link expires in 24 hours.

Best,
The NexroCampus Team
"""
    
    return await send_email(email, subject, html_content, text_content)


# ============================================
# SEND PASSWORD RESET EMAIL (NEW)
# ============================================

async def send_password_reset_email(email: str, full_name: str, token: str):
    """Send beautiful password reset email"""
    
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    
    subject = "Reset your NexroCampus password 🔒"
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background-color: #f3f4f6;
        }}
        .container {{
            max-width: 600px;
            margin: 40px auto;
            background: #ffffff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            padding: 40px 30px;
            text-align: center;
        }}
        .logo {{
            color: #ffffff;
            font-size: 32px;
            font-weight: bold;
            margin: 0;
        }}
        .content {{
            padding: 40px 30px;
        }}
        .greeting {{
            color: #1f2937;
            font-size: 24px;
            font-weight: 600;
            margin: 0 0 16px 0;
        }}
        .text {{
            color: #4b5563;
            font-size: 16px;
            line-height: 24px;
            margin: 16px 0;
        }}
        .button-container {{
            text-align: center;
            margin: 32px 0;
        }}
        .button {{
            display: inline-block;
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            color: #ffffff;
            text-decoration: none;
            padding: 14px 40px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 16px;
        }}
        .warning {{
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 12px 16px;
            border-radius: 4px;
            margin: 16px 0;
            color: #78350f;
            font-size: 13px;
        }}
        .danger {{
            background: #fee2e2;
            border-left: 4px solid #dc2626;
            padding: 12px 16px;
            border-radius: 4px;
            margin: 16px 0;
            color: #7f1d1d;
            font-size: 13px;
        }}
        .footer {{
            background: #f9fafb;
            padding: 24px 30px;
            text-align: center;
            border-top: 1px solid #e5e7eb;
        }}
        .footer-text {{
            color: #6b7280;
            font-size: 12px;
            margin: 4px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="logo">🔒 Password Reset</h1>
        </div>
        <div class="content">
            <h2 class="greeting">Hi {full_name},</h2>
            
            <p class="text">
                We received a request to reset your NexroCampus account password. 
                If you made this request, click the button below to set a new password:
            </p>
            
            <div class="button-container">
                <a href="{reset_url}" class="button">
                    🔑 Reset Password
                </a>
            </div>
            
            <p class="text" style="text-align: center; color: #6b7280;">
                Or copy this link: {reset_url}
            </p>
            
            <div class="warning">
                ⏰ <strong>This link expires in 1 hour</strong> for security reasons.
            </div>
            
            <div class="danger">
                🚨 <strong>Didn't request this?</strong> 
                If you didn't ask to reset your password, you can safely ignore this email. 
                Your password will remain unchanged.
            </div>
        </div>
        <div class="footer">
            <p class="footer-text">© 2024 NexroCampus. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""
    
    text_content = f"""
Password Reset Request 🔒

Hi {full_name},

We received a request to reset your NexroCampus password.

Click this link to reset your password:
{reset_url}

⏰ This link expires in 1 hour.

🚨 If you didn't request this, please ignore this email. Your password will remain unchanged.

Best,
The NexroCampus Team
"""
    
    return await send_email(email, subject, html_content, text_content)


# ============================================
# SEND PASSWORD CHANGED CONFIRMATION (BONUS)
# ============================================

async def send_password_changed_email(email: str, full_name: str):
    """Notify user that password was changed"""
    
    subject = "Your NexroCampus password was changed ✅"
    
    html_content = f"""
<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, sans-serif; background-color: #f3f4f6; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 40px;">
        <h1 style="color: #10b981; text-align: center;">✅ Password Changed</h1>
        
        <h2 style="color: #1f2937;">Hi {full_name},</h2>
        
        <p style="color: #4b5563; font-size: 16px; line-height: 24px;">
            Your NexroCampus password was successfully changed.
        </p>
        
        <p style="color: #4b5563; font-size: 16px; line-height: 24px;">
            You can now log in with your new password.
        </p>
        
        <div style="background: #fee2e2; border-left: 4px solid #dc2626; padding: 12px; border-radius: 4px; margin: 20px 0;">
            <strong style="color: #7f1d1d;">🚨 Wasn't you?</strong>
            <p style="color: #7f1d1d; margin: 8px 0 0 0;">
                If you didn't change this password, please contact us immediately 
                at support@nexrocampus.com
            </p>
        </div>
        
        <p style="color: #6b7280; font-size: 12px; margin-top: 30px;">
            © 2024 NexroCampus. All rights reserved.
        </p>
    </div>
</body>
</html>
"""
    
    text_content = f"""
Password Changed ✅

Hi {full_name},

Your NexroCampus password was successfully changed.

You can now log in with your new password.

🚨 Wasn't you? Contact support@nexrocampus.com immediately.

Best,
The NexroCampus Team
"""
    
    return await send_email(email, subject, html_content, text_content)