#!/usr/bin/env python3
"""
Simple test script to verify the YouTube Shorts Creator setup.
"""

import os
import sys
from pathlib import Path

def test_imports():
    """Test if all required modules can be imported."""
    print("Testing imports...")
    
    try:
        from google.adk.agents import Agent, BaseAgent
        print("✅ Google ADK imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Google ADK: {e}")
        return False
    
    try:
        import streamlit as st
        print("✅ Streamlit imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Streamlit: {e}")
        return False
    
    try:
        from app.agent import root_agent
        print("✅ App agent imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import app agent: {e}")
        return False
    
    return True

def test_environment():
    """Test environment setup."""
    print("\nTesting environment...")
    
    # Check if .env file exists
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file found")
    else:
        print("⚠️  .env file not found. You'll need to create one with your GOOGLE_API_KEY")
    
    # Check if projects directory exists
    projects_dir = Path("projects")
    if projects_dir.exists():
        print("✅ projects directory exists")
    else:
        print("ℹ️  projects directory will be created automatically")
    
    return True

def test_api_key():
    """Test if API key is available."""
    print("\nTesting API key...")
    
    api_key = os.environ.get("GOOGLE_API_KEY")
    if api_key:
        print("✅ GOOGLE_API_KEY found in environment")
        return True
    else:
        print("❌ GOOGLE_API_KEY not found in environment")
        print("   Please set it in your .env file or environment variables")
        return False

def main():
    """Run all tests."""
    print("🧪 YouTube Shorts Creator Setup Test")
    print("=" * 40)
    
    success = True
    
    if not test_imports():
        success = False
    
    if not test_environment():
        success = False
    
    if not test_api_key():
        success = False
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 All tests passed! Your setup looks good.")
        print("\nTo run the application:")
        print("1. make install")
        print("2. make dev-app")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main() 