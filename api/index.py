"""
Vercel serverless entry point for Flask app.
"""
from app import create_app

app = create_app()
