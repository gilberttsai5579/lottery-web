#!/usr/bin/env python3
"""
Startup script for lottery web application
"""
from app import create_app

if __name__ == '__main__':
    import socket
    
    # Find available port
    def find_free_port(start_port=5000):
        for port in range(start_port, start_port + 100):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('127.0.0.1', port))
                sock.close()
                return port
            except OSError:
                continue
        return 8080  # fallback port
    
    port = find_free_port()
    
    app = create_app()
    print("🎯 Lottery Web Application Starting...")
    print(f"📱 Access the application at: http://localhost:{port}")
    print("🔗 API Documentation: Check CLAUDE.md for development guidelines")
    print(f"🔧 Using port {port} (5000 was occupied)")
    
    # Use 127.0.0.1 instead of 0.0.0.0 for better security
    app.run(host='127.0.0.1', port=port, debug=True, use_reloader=False)