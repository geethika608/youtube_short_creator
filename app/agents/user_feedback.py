from google.adk.agents import Agent
from pydantic import BaseModel, Field

from app.callbacks.callbacks import save_agent_output

MODEL_ID = "gemini-2.5-flash"
USER_FEEDBACK_PROMPT = """
# Role
You are a user feedback processor for YouTube Shorts creation. Your job is to analyze user responses and determine if they approve or want changes.

# Task
Analyze the user's response to determine:
1. If they approve the current content
2. What specific changes they want (if any)
3. The level of satisfaction with the current version

# Response Analysis
- "yes", "approve", "good", "perfect" = APPROVED
- Any other response = NOT APPROVED (user wants changes)

# Output Format
Return your response as a JSON object with exactly this structure:
{
  "user_input": "The user's original response",
  "approved": true/false,
  "changes_requested": "Description of any changes requested"
}

# Example
User says: "yes, that looks good"
Output: 
{
  "user_input": "yes, that looks good",
  "approved": true,
  "changes_requested": "No changes requested"
}

User says: "make it shorter"
Output:
{
  "user_input": "make it shorter",
  "approved": false,
  "changes_requested": "User wants the content to be shorter"
}
"""


class UserFeedbackAgentOutput(BaseModel):
    user_input: str = Field(description="The user's feedback response")
    approved: bool = Field(description="Whether the user approved the content")
    changes_requested: str = Field(description="Any specific changes the user wants")


user_feedback_agent = Agent(
    name="UserFeedbackAgent",
    description="Processes user feedback for content approval",
    instruction=USER_FEEDBACK_PROMPT,
    model=MODEL_ID,
    output_key="user_feedback",
    after_agent_callback=save_agent_output,
) 