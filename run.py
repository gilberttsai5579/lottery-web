#!/usr/bin/env python3
"""
Startup script for lottery web application
"""
from app import create_app

if __name__ == '__main__':
    app = create_app()
    print("🎯 Lottery Web Application Starting...")
    print("📱 Access the application at: http://localhost:5000")
    print("🔗 API Documentation: Check CLAUDE.md for development guidelines")
    app.run(host='0.0.0.0', port=5000, debug=True)