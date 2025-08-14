#!/usr/bin/env python3
"""Test script to debug app startup"""
import os
import sys

print("Starting test app...")
print(f"Python path: {sys.executable}")
print(f"Working directory: {os.getcwd()}")
print(f"TELEGRAM_TOKEN exists: {'TELEGRAM_TOKEN' in os.environ}")

try:
    # Import only what we need for basic Flask app
    from flask import Flask, jsonify
    print("Flask imported successfully")
    
    app = Flask(__name__)
    
    @app.route('/')
    def index():
        return jsonify({'status': 'test app running'})
    
    @app.route('/health')
    def health():
        return jsonify({'status': 'healthy'})
    
    print("Starting Flask on port 8000...")
    app.run(host='0.0.0.0', port=8000, debug=False)
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()