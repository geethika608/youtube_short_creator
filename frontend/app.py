"""
YouTube Shorts Creator - Streamlit Frontend
===========================================

A user-friendly chat interface for creating YouTube Shorts using AI agents.
"""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="YouTube Shorts Creator",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="expanded",
)

# Constants
API_BASE_URL = "http://localhost:8000"
APP_NAME = "app"

# Initialize session state
if "user_id" not in st.session_state:
    st.session_state.user_id: str = f"user-{uuid.uuid4()}"

if "session_id" not in st.session_state:
    st.session_state.session_id: Optional[str] = None

if "messages" not in st.session_state:
    st.session_state.messages: List[Dict[str, Any]] = []


def create_session() -> bool:
    """Create a new session with the ADK agent."""
    session_id = f"session-{int(time.time())}"
    try:
        response = requests.post(
            f"{API_BASE_URL}/apps/{APP_NAME}/users/{st.session_state.user_id}/sessions/{session_id}",
            headers={"Content-Type": "application/json"},
            json={},
            timeout=10,
        )
        response.raise_for_status()

        st.session_state.session_id = session_id
        st.session_state.messages = []
        st.success(f"New session created: {session_id}")
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to create session: {e}. Is the backend running?")
        return False


def send_message(message: str) -> None:
    """Send a message to the agent and handle the response."""
    if not st.session_state.session_id:
        st.error("No active session. Please create a session first.")
        return

    st.session_state.messages.append({"role": "user", "content": message})

    try:
        with st.spinner("AI is creating your YouTube Short..."):
            response = requests.post(
                f"{API_BASE_URL}/run",
                headers={"Content-Type": "application/json"},
                json={
                    "app_name": APP_NAME,
                    "user_id": st.session_state.user_id,
                    "session_id": st.session_state.session_id,
                    "new_message": {"role": "user", "parts": [{"text": message}]},
                },
                timeout=300,  # 5 minute timeout
            )
            response.raise_for_status()

        events = response.json()
        assistant_messages_added = 0
        
        for event in events:
            content = event.get("content")

            # Skip user messages
            if content and content.get("role") == "user":
                continue

            # Process text content
            if content and content.get("parts"):
                for part in content.get("parts", []):
                    if "text" in part:
                        text_content = part["text"].strip()
                        if text_content:
                            st.session_state.messages.append(
                                {"role": "assistant", "content": text_content}
                            )
                            assistant_messages_added += 1

        if assistant_messages_added == 0 and events:
            assistant_message = "The agent responded, but no text message was found."
            st.session_state.messages.append(
                {"role": "assistant", "content": assistant_message}
            )

    except requests.exceptions.RequestException as e:
        st.error(f"Network error: {e}. Is the backend running on {API_BASE_URL}?")
        logger.error(f"RequestException: {e}", exc_info=True)
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        logger.error(f"Unexpected error: {e}", exc_info=True)


# UI Rendering
st.title("🎬 YouTube Shorts Creator")
st.caption("AI-Powered YouTube Shorts Video Generator")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("🎛️ Controls")
    
    if st.button("🆕 New Session", type="primary"):
        create_session()
        st.rerun()
    
    st.info(f"**Session ID:** {st.session_state.session_id or 'None'}")
    
    st.markdown("---")
    st.markdown("### 📋 How to Use")
    st.markdown("""
    1. **Create a session** using the button above
    2. **Describe your video** in the chat (e.g., "Create a video about cooking pasta")
    3. **Review and approve** the theme and script
    4. **Wait for generation** of images and assets
    5. **Check your project folder** for the final content
    """)

# Main chat interface
st.subheader("💬 Start by describing the YouTube Short you want to create")

# Display chat messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Chat input
if st.session_state.session_id:
    if user_input := st.chat_input("Describe your YouTube Short idea..."):
        send_message(user_input)
        st.rerun()
else:
    st.info("👈 Create a new session to begin creating YouTube Shorts!")

# Footer
st.markdown("---")
st.markdown("*Built with Google's Agent Development Kit and Streamlit*") 