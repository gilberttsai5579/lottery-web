#!/usr/bin/env python3
"""
Debug script for lottery web application
Helps diagnose and fix common issues
"""
import os
import sys
import socket
import subprocess

def check_port(port):
    """Check if port is available"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result != 0  # True if port is free
    except:
        return False

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        'flask', 'flask_cors', 'requests', 
        'beautifulsoup4', 'openpyxl'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    return missing

def check_file_structure():
    """Check if required files exist"""
    required_files = [
        'app.py', 'run.py', 'config.py',
        'src/main/python/models/__init__.py',
        'src/main/python/services/__init__.py',
        'templates/index.html'
    ]
    
    missing = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing.append(file_path)
    
    return missing

def test_imports():
    """Test if app imports work"""
    try:
        from app import create_app
        app = create_app()
        return True, "All imports successful"
    except Exception as e:
        return False, str(e)

def find_free_port(start_port=5001):
    """Find an available port"""
    for port in range(start_port, start_port + 100):
        if check_port(port):
            return port
    return None

def main():
    print("🔧 Lottery Web Application Debug Tool")
    print("=" * 50)
    
    # Check working directory
    print(f"📁 Current directory: {os.getcwd()}")
    if not os.path.exists('app.py'):
        print("❌ Not in lottery-web directory!")
        print("💡 Please run: cd lottery-web")
        return
    
    # Check virtual environment
    if 'venv' in sys.executable or 'VIRTUAL_ENV' in os.environ:
        print("✅ Virtual environment activated")
    else:
        print("⚠️  Virtual environment not detected")
        print("💡 Please run: source venv/bin/activate")
    
    # Check dependencies
    print("\n🔍 Checking dependencies...")
    missing_deps = check_dependencies()
    if missing_deps:
        print(f"❌ Missing packages: {', '.join(missing_deps)}")
        print("💡 Please run: pip install " + " ".join(missing_deps))
    else:
        print("✅ All dependencies installed")
    
    # Check file structure
    print("\n📂 Checking file structure...")
    missing_files = check_file_structure()
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
    else:
        print("✅ All required files present")
    
    # Test imports
    print("\n🧪 Testing imports...")
    import_success, import_msg = test_imports()
    if import_success:
        print("✅ App imports working")
    else:
        print(f"❌ Import error: {import_msg}")
    
    # Check ports
    print("\n🔌 Checking ports...")
    port_5000_free = check_port(5000)
    if port_5000_free:
        print("✅ Port 5000 is available")
        suggested_port = 5000
    else:
        print("⚠️  Port 5000 is occupied (likely by ControlCenter)")
        suggested_port = find_free_port()
        if suggested_port:
            print(f"✅ Port {suggested_port} is available")
        else:
            print("❌ No free ports found")
    
    # Summary and recommendations
    print("\n📋 Summary:")
    if import_success and not missing_deps and not missing_files:
        print("🎉 Application should work!")
        print(f"🚀 Try running: python run.py")
        if suggested_port != 5000:
            print(f"📱 Access at: http://localhost:{suggested_port}")
    else:
        print("🔧 Issues found - please fix the above problems first")
    
    print("\n💡 Quick fixes:")
    print("1. Ensure virtual environment: source venv/bin/activate")
    print("2. Install dependencies: pip install Flask Flask-CORS requests beautifulsoup4 openpyxl python-dotenv")
    print("3. Run application: python run.py")

if __name__ == "__main__":
    main()