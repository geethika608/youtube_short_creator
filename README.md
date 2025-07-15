# YouTube Shorts Creator

A simplified AI-powered YouTube Shorts video generator built with Google's Agent Development Kit (ADK).

## Features

- **AI-Powered Content Creation**: Generate videos from simple text prompts
- **Multi-Agent Workflow**: Coordinated agents for research, scriptwriting, and asset generation
- **Google AI Integration**: Uses Gemini, Imagen, and Veo models
- **Interactive UI**: Streamlit-based chat interface
- **User Feedback Loops**: Approve themes and scripts before generation

## Quick Start

1. **Install dependencies:**
   ```bash
   make install
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env
   # Add your GOOGLE_API_KEY to .env
   ```

3. **Run the application:**
   ```bash
   make dev-app
   ```

4. **Open your browser** to the Streamlit URL (usually `http://localhost:8501`)

## How It Works

1. **User Input**: Describe the video you want to create
2. **Theme Definition**: AI proposes a theme for your approval
3. **Research**: Gather information about the topic
4. **Script Writing**: Create a script based on research
5. **Asset Generation**: Generate images, videos, and voiceovers
6. **Video Assembly**: Combine everything into a final video

## Project Structure

```
youtube_shorts_creator/
├── app/
│   ├── agents/          # Specialized AI agents
│   ├── utils/           # Utility functions
│   └── agent.py         # Main orchestrator agent
├── frontend/
│   └── app.py           # Streamlit UI
└── projects/            # Generated videos and assets
``` 