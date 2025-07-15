from google.adk.agents import Agent
from pydantic import BaseModel, Field

from app.callbacks.callbacks import save_agent_output

MODEL_ID = "gemini-2.5-flash"
THEME_DEFINER_PROMPT = """
# Role
You are an expert content strategist specializing in YouTube Shorts. Your job is to understand user requests and create engaging, viral-worthy video themes.

# Task
Analyze the user's request and create:
1. A concise theme (1-3 words)
2. A detailed user intent that captures their vision

# Output Format
Return your response as a JSON object with exactly this structure:
{
  "theme": "Your theme here (1-3 words)",
  "user_intent": "Detailed description of what the user wants"
}

# Example
User: "I want a video about cooking pasta"
Output: 
{
  "theme": "Pasta Cooking",
  "user_intent": "Create an engaging YouTube Short about cooking pasta, showing quick tips and techniques that viewers can easily follow"
}

# Constraints
- Theme must be 1-3 words
- Intent should be comprehensive and specific
- Focus on YouTube Shorts format (vertical, engaging, under 60 seconds)
- Always return valid JSON
"""


class ThemeDefinerAgentOutput(BaseModel):
    theme: str = Field(description="The theme of the YouTube Short (1-3 words)")
    user_intent: str = Field(description="Detailed user intent for video creation")


theme_definer_agent = Agent(
    name="ThemeDefinerAgent",
    description="Defines the theme and intent for YouTube Shorts videos",
    instruction=THEME_DEFINER_PROMPT,
    model=MODEL_ID,
    output_key="theme_intent",
    after_agent_callback=save_agent_output,
) 