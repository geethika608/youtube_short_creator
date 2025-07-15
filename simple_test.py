#!/usr/bin/env python3
"""
Simple test to verify the basic agent setup works.
"""

import os
import sys
from pathlib import Path

def test_basic_imports():
    """Test basic imports without running agents."""
    print("Testing basic imports...")
    
    try:
        from google.adk.agents import Agent
        print("✅ Google ADK Agent imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Google ADK Agent: {e}")
        return False
    
    try:
        from app.agents.theme_definer import theme_definer_agent
        print("✅ Theme definer agent imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import theme definer agent: {e}")
        return False
    
    try:
        from app.agents.user_feedback import user_feedback_agent
        print("✅ User feedback agent imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import user feedback agent: {e}")
        return False
    
    return True

def test_agent_creation():
    """Test that agents can be created without errors."""
    print("\nTesting agent creation...")
    
    try:
        from app.agents.theme_definer import theme_definer_agent
        from app.agents.user_feedback import user_feedback_agent
        
        # Just verify they exist and have the right attributes
        assert hasattr(theme_definer_agent, 'name')
        assert hasattr(theme_definer_agent, 'output_key')
        assert hasattr(user_feedback_agent, 'name')
        assert hasattr(user_feedback_agent, 'output_key')
        
        print("✅ Agents created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create agents: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Simple YouTube Shorts Creator Test")
    print("=" * 40)
    
    success = True
    
    if not test_basic_imports():
        success = False
    
    if not test_agent_creation():
        success = False
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 Basic tests passed! The setup should work.")
        print("\nNext steps:")
        print("1. Make sure you have a valid GOOGLE_API_KEY in your .env file")
        print("2. Try running: make dev-app")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main() 