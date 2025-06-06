# Email Notifications for InvenTree Order Calculator

This document describes the automated email notification feature for the InvenTree Order Calculator tool.

## Overview

The email notification feature allows you to:
- Send automated email reports with calculation results
- Schedule regular reports (daily, weekly, monthly)
- Use existing presets for automated calculations
- Customize email content and formatting
- Test email configuration before deployment

## Features

### Email Configuration
- **SMTP Settings**: Configure your email server (host, port, security)
- **Authentication**: Username and password for SMTP authentication
- **Recipients**: Multiple recipients with TO, CC, and BCC support
- **Sender Configuration**: Customize sender name and email address
- **Subject Templates**: Use dynamic placeholders in subject lines

### Report Formatting
- **HTML and Plain Text**: Dual format emails for compatibility
- **Table Formatting**: Professional table layouts for parts and assemblies
- **Summary Statistics**: Overview of calculation results
- **Warning Messages**: Include any calculation warnings
- **Customizable Content**: Choose which sections to include

### Scheduling
- **Multiple Frequencies**: Daily, weekly, or monthly reports
- **Time Configuration**: Specify exact time of day for sending
- **Timezone Support**: Configure timezone for accurate scheduling
- **Preset Integration**: Use existing calculation presets for automation

### Testing and Validation
- **Connection Testing**: Verify SMTP settings before use
- **Test Emails**: Send sample emails to verify configuration
- **Send Now**: Manual report sending for immediate results
- **Configuration Validation**: Real-time validation of settings

## Setup Guide

### 1. Access Advanced Settings

1. Open the InvenTree Order Calculator application
2. In the sidebar, click the "⚙️ Advanced Settings" button
3. The email configuration dialog will open

### 2. Configure SMTP Settings

In the **Email Config** tab:

1. **SMTP Host**: Enter your email server hostname (e.g., `smtp.gmail.com`)
2. **SMTP Port**: Enter the port number (587 for TLS, 465 for SSL, 25 for none)
3. **Security**: Choose TLS, SSL, or None based on your server
4. **Username**: Your email account username
5. **Password**: Your email account password
6. **Sender Email**: The email address to send from
7. **Sender Name**: Display name for the sender

### 3. Configure Recipients

1. **To**: Enter primary recipients (one email per line)
2. **CC**: Enter CC recipients (optional, one email per line)
3. **BCC**: Enter BCC recipients (optional, one email per line)

### 4. Customize Content

Choose which sections to include in your emails:
- **Include Parts Table**: Parts that need to be ordered
- **Include Assemblies Table**: Assemblies that need to be built
- **Include Summary**: Summary statistics

### 5. Set Up Scheduling (Optional)

In the **Schedule** tab:

1. **Enable Automated Email Reports**: Check to enable scheduling
2. **Frequency**: Choose Daily, Weekly, or Monthly
3. **Time of Day**: Set the time to send reports
4. **Timezone**: Configure your timezone
5. **Preset to Use**: Select which preset to use for calculations

### 6. Test Configuration

In the **Test** tab:

1. **Test SMTP Connection**: Verify server connectivity
2. **Send Test Email**: Send a sample email to verify settings
3. **Send Current Results**: Send a report with current calculation results
4. **Calculate & Send**: Calculate results for a specific preset and send

## Email Templates

### Subject Line Templates

Use Jinja2 template syntax in subject lines:
- `{{date}}` - Current date (YYYY-MM-DD)
- `{{time}}` - Current time (HH:MM)
- `{{preset}}` - Name of the preset used

Examples:
- `InvenTree Order Report - {{date}}`
- `Weekly Report for {{preset}} - {{date}}`
- `Daily Orders {{date}} at {{time}}`

### Email Content

The email includes:
- **Header**: Report title and preset information
- **Summary**: Statistics about parts and assemblies
- **Warnings**: Any calculation warnings
- **Parts Table**: Detailed parts to order with suppliers
- **Assemblies Table**: Assemblies to build with quantities
- **Footer**: Automated generation notice

## Common SMTP Configurations

### Gmail
- **Host**: `smtp.gmail.com`
- **Port**: `587`
- **Security**: `TLS`
- **Note**: Use App Password instead of regular password

### Outlook/Hotmail
- **Host**: `smtp-mail.outlook.com`
- **Port**: `587`
- **Security**: `TLS`

### Yahoo Mail
- **Host**: `smtp.mail.yahoo.com`
- **Port**: `587` or `465`
- **Security**: `TLS` or `SSL`

### Custom SMTP Server
- Configure according to your server specifications
- Contact your IT administrator for settings

## Troubleshooting

### Connection Issues
1. Verify SMTP host and port settings
2. Check firewall and network connectivity
3. Ensure correct security protocol (TLS/SSL)
4. Test with email client first

### Authentication Errors
1. Verify username and password
2. Check if two-factor authentication is enabled
3. Use app-specific passwords when required
4. Ensure account allows SMTP access

### Email Not Received
1. Check spam/junk folders
2. Verify recipient email addresses
3. Check email server logs
4. Test with different recipients

### Scheduling Issues
1. Verify timezone settings
2. Check that scheduler is running
3. Ensure preset exists and is valid
4. Review application logs

## Security Considerations

1. **Password Storage**: Email passwords are stored in configuration files
2. **File Permissions**: Ensure configuration files have appropriate permissions
3. **Network Security**: Use TLS/SSL when possible
4. **Access Control**: Limit access to configuration settings
5. **App Passwords**: Use app-specific passwords for enhanced security

## API Reference

### Configuration Classes
- `EmailConfig`: Complete email configuration
- `SMTPConfig`: SMTP server settings
- `EmailRecipients`: Recipient configuration
- `ScheduleConfig`: Scheduling settings

### Core Classes
- `EmailSender`: Handles email sending
- `EmailFormatter`: Formats email content
- `EmailScheduler`: Manages scheduling
- `EmailConfigManager`: Configuration persistence

### Usage Example

```python
from inventree_order_calculator.email_config import EmailConfig, SMTPConfig, EmailRecipients
from inventree_order_calculator.email_sender import EmailSender

# Create configuration
smtp = SMTPConfig(
    host="smtp.gmail.com",
    port=587,
    username="your-email@gmail.com",
    password="your-app-password",
    security="tls"
)

recipients = EmailRecipients(
    to=["recipient@example.com"]
)

config = EmailConfig(
    smtp=smtp,
    sender_email="your-email@gmail.com",
    recipients=recipients
)

# Send email
sender = EmailSender(config)
sender.send_report(calculation_results, "My Preset")
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review application logs for error messages
3. Test with minimal configuration first
4. Verify email server settings with your provider
