# Orders Mobile App

A mobile-friendly web application for managing orders, customers, and generating labels.

## Environment Variables

### Required for Production (Supabase)

Set these environment variables in your deployment platform (Render, Heroku, etc.):

- `SUPABASE_URL`: Your Supabase PostgreSQL connection string
  - Format: `postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres`
  - Use the transaction pooler URL, not the direct connection
- `SECRET_KEY`: Flask secret key for session management

### Local Development

For local development, you can:
1. Use SQLite (default) - no environment variables needed
2. Use Supabase - set `SUPABASE_URL` in your environment

## Security Notice

⚠️ **IMPORTANT**: Never commit database credentials to version control!

- The `SUPABASE_URL` contains your database password
- Always use environment variables for sensitive data
- Check your deployment platform's documentation for setting environment variables

## Getting Started

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set environment variables (see above)
4. Run the application: `python app.py`

## Features

- 📱 Mobile-friendly interface
- 👥 Customer management
- 📋 Order tracking
- 🏷️ Label generation
- 📊 News/activity feed
- 🔐 User authentication 