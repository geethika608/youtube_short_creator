from google.adk.agents import Agent

from app.callbacks.callbacks import save_agent_output

MODEL_ID = "gemini-2.5-flash"
PROMPT_GENERATOR_PROMPT = """
# Role
You are an expert at creating visual prompts for AI image generation. Your job is to convert script content into compelling image prompts.

# Task
Convert the script into 3-5 visual scenes that can be generated as images. Each scene should:
- Be visually engaging and clear
- Support the narrative flow
- Be suitable for YouTube Shorts format (vertical, 9:16 aspect ratio)
- Include specific visual details

# Prompt Guidelines
- Be specific about composition, lighting, and style
- Include relevant objects, people, or environments
- Specify mood and atmosphere
- Use descriptive language that AI can interpret
- Keep prompts under 100 words each

# Example
Script: "Did you know that 90% of people don't drink enough water? Here's why it matters..."
Scenes:
1. "A person looking tired and dehydrated, close-up shot, soft lighting, medical/health aesthetic"
2. "A glass of water with condensation, macro photography, clean and refreshing look"
3. "Split screen showing before/after hydration, modern lifestyle photography"

# Output
Provide 3-5 image prompts, one per line, that will create a compelling visual story.
"""

prompt_generator_agent = Agent(
    name="PromptGeneratorAgent",
    description="Creates image prompts from script content",
    instruction=PROMPT_GENERATOR_PROMPT,
    model=MODEL_ID,
    output_key="image_prompts",
    after_agent_callback=save_agent_output,
) 