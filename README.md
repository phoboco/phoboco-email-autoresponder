# PhoBoCo Email Autoresponder

This is an intelligent Gmail autoresponder for PhoBoCo’s inbox at `booking@phoboco.com`. It scans labeled emails, uses OpenAI to generate responses, and saves replies as Gmail drafts for manual review.

## 🔧 Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements_email_autoresponder.txt
   ```

## Google API Setup

Enable the Gmail API at https://console.cloud.google.com/

Create OAuth 2.0 credentials for a "Desktop App"

Download `credentials.json` and place it in the same directory

First run will trigger a browser auth window and save `token.json`

## OpenAI API Key

Set your key in your shell:

```bash
export OPENAI_API_KEY='YOUR_OPENAI_API_KEY'

## Run the Script

```bash
python email_autoresponder.py
```

## Schedule (Cron Example)

```cron
0 8 * * * /usr/bin/python3 /path/to/email_autoresponder.py
0 14 * * * /usr/bin/python3 /path/to/email_autoresponder.py
```

## 🔐 Labels Expected in Gmail

- Leads_New
- Clients_OpenQuestions
- Finance_Bookings
- Event_Changes

Responses will only be drafted for unread emails with these labels.
