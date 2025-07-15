import json
import logging
from enum import Enum
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv
from google.adk.agents import Agent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from typing_extensions import override

from app.agents.image_generator import image_generator_agent
from app.agents.prompt_generator import prompt_generator_agent
from app.agents.researcher import researcher_agent
from app.agents.script_writer import script_writer_agent
from app.agents.theme_definer import theme_definer_agent
from app.agents.user_feedback import user_feedback_agent
from app.utils.genai_utils import text2event

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WorkflowStage(Enum):
    THEME_DEFINITION = 1
    RESEARCH = 2
    SCRIPT_CREATION = 3
    ASSET_GENERATION = 4


class YouTubeShortsCreatorAgent(BaseAgent):
    """Orchestrates the YouTube Shorts creation workflow."""

    theme_definer: Agent
    user_feedback: Agent
    researcher: Agent
    script_writer: Agent
    prompt_generator: Agent

    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}

    def __init__(
        self,
        name: str,
        theme_definer: Agent,
        user_feedback: Agent,
        researcher: Agent,
        script_writer: Agent,
        prompt_generator: Agent,
    ):
        """Initialize the YouTube Shorts Creator Agent."""
        sub_agents_list = [
            theme_definer,
            user_feedback,
            researcher,
            script_writer,
            prompt_generator,
        ]

        super().__init__(
            name=name,
            theme_definer=theme_definer,
            user_feedback=user_feedback,
            researcher=researcher,
            script_writer=script_writer,
            prompt_generator=prompt_generator,
            sub_agents=sub_agents_list,
        )
        # Instantiate the image generator as a regular attribute
        self.image_generator = image_generator_agent

    async def _run_sub_agent(
        self, agent: BaseAgent, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Run a sub-agent and yield its events."""
        logger.info(f"[{self.name}] Running {agent.name}...")

        async for event in agent.run_async(ctx):
            yield event

        agent_output = ctx.session.state.get(agent.output_key)
        if not agent_output:
            error_msg = f"[{self.name}] {agent.name} did not produce output. Aborting workflow."
            logger.error(error_msg)
            yield text2event(self.name, error_msg)
            return

        logger.info(f"[{self.name}] {agent.name} completed successfully.")

    def _parse_json_response(self, raw_data, context=""):
        """Parse JSON response, handling markdown wrapping."""
        try:
            if isinstance(raw_data, str):
                json_str = raw_data.strip()
                if json_str.startswith("```json"):
                    json_str = json_str[7:]
                if json_str.endswith("```"):
                    json_str = json_str[:-3]
                json_str = json_str.strip()
                return json.loads(json_str)
            else:
                return raw_data
        except (json.JSONDecodeError, AttributeError) as e:
            logger.error(f"[{self.name}] JSON parsing failed for {context}: {e}, Raw data: {raw_data}")
            return None

    def _is_user_approval(self, user_input):
        """Check if user input indicates approval."""
        if not user_input:
            return False
        return user_input.lower().strip() in ["yes", "approve", "good", "perfect", "ok", "okay"]

    async def _define_theme_and_ask_for_feedback(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Define theme and ask for user feedback."""
        yield text2event(self.name, "Let me analyze your request and propose a theme...")
        
        async for event in self._run_sub_agent(self.theme_definer, ctx):
            yield event

        theme_intent_raw = ctx.session.state.get(self.theme_definer.output_key)
        if theme_intent_raw:
            theme_intent = self._parse_json_response(theme_intent_raw, "theme")
            if theme_intent:
                theme = theme_intent.get("theme", "Unknown Theme")
                intent = theme_intent.get("user_intent", "No intent specified")
                
                yield text2event(
                    self.name,
                    f"I propose this theme: **{theme}**\n\n"
                    f"Intent: {intent}\n\n"
                    f"Does this look good to you? Type 'yes' to approve or provide feedback for changes."
                )
            else:
                yield text2event(self.name, "Sorry, I couldn't understand your request. Please try again.")

    async def _draft_script_and_ask_for_feedback(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Draft script and ask for user feedback."""
        yield text2event(self.name, "Creating your script based on the research...")
        
        async for event in self._run_sub_agent(self.script_writer, ctx):
            yield event

        script = ctx.session.state.get(self.script_writer.output_key)
        if script:
            yield text2event(
                self.name,
                f"Here's your script:\n\n**{script}**\n\n"
                f"Does this script work for you? Type 'yes' to approve or provide feedback for changes."
            )

    async def _setup_assets_folder(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Set up the assets folder for the project."""
        theme_intent_raw = ctx.session.state.get(self.theme_definer.output_key)
        if not theme_intent_raw:
            yield text2event(self.name, "Error: No theme defined")
            return

        theme_intent = self._parse_json_response(theme_intent_raw, "theme setup")
        if theme_intent:
            theme = theme_intent.get("theme", "default")
            intent = theme_intent.get("user_intent", "")
        else:
            theme = "default"
            intent = ""
        
        assets_path = Path("projects") / theme.replace(" ", "_").lower()
        assets_path.mkdir(parents=True, exist_ok=True)
        
        ctx.session.state["assets_path"] = str(assets_path)
        ctx.session.state["intent"] = intent

        yield text2event(self.name, f"Project folder created: {assets_path}")

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Execute the main YouTube Shorts creation workflow."""
        logger.info(f"[{self.name}] Starting YouTube Shorts creation workflow.")

        # Get current workflow stage
        current_stage = ctx.session.state.get("workflow_stage", WorkflowStage.THEME_DEFINITION)
        logger.info(f"[{self.name}] Current workflow stage: {current_stage}")

        if current_stage == WorkflowStage.THEME_DEFINITION:
            # Check if we have a theme defined
            theme_intent = ctx.session.state.get(self.theme_definer.output_key)
            
            if not theme_intent:
                # First time - define theme
                async for event in self._define_theme_and_ask_for_feedback(ctx):
                    yield event
                return
            else:
                # Theme exists, check if user has responded
                user_responded = ctx.session.state.get("user_responded_to_theme", False)
                
                if not user_responded:
                    # Check if we have user input to process
                    user_feedback_raw = ctx.session.state.get(self.user_feedback.output_key)
                    if user_feedback_raw:
                        # Process user feedback
                        async for event in self._run_sub_agent(self.user_feedback, ctx):
                            yield event
                        
                        # Extract user input from feedback
                        user_feedback_data = self._parse_json_response(user_feedback_raw, "user feedback")
                        if user_feedback_data:
                            user_input = user_feedback_data.get("user_input", "")
                            ctx.session.state["user_feedback"] = user_input
                            ctx.session.state["user_responded_to_theme"] = True
                            
                            # Check if approved
                            if self._is_user_approval(user_input):
                                # Theme approved, move to research
                                ctx.session.state["workflow_stage"] = WorkflowStage.RESEARCH
                                yield text2event(self.name, "Theme approved! Moving to research...")
                                
                                async for event in self._setup_assets_folder(ctx):
                                    yield event
                                
                                yield text2event(self.name, "Researching your topic...")
                                async for event in self._run_sub_agent(self.researcher, ctx):
                                    yield event
                                
                                ctx.session.state["workflow_stage"] = WorkflowStage.SCRIPT_CREATION
                                yield text2event(self.name, "Research complete! Creating your script...")
                                async for event in self._draft_script_and_ask_for_feedback(ctx):
                                    yield event
                                return
                            else:
                                # Theme not approved, regenerate
                                yield text2event(self.name, "I'll revise the theme based on your feedback...")
                                # Clear the old theme and reset state
                                ctx.session.state.pop(self.theme_definer.output_key, None)
                                ctx.session.state["user_responded_to_theme"] = False
                                ctx.session.state["user_feedback"] = ""
                                async for event in self._define_theme_and_ask_for_feedback(ctx):
                                    yield event
                                return
                    else:
                        # No user feedback yet, show theme again
                        async for event in self._define_theme_and_ask_for_feedback(ctx):
                            yield event
                        return

        elif current_stage == WorkflowStage.SCRIPT_CREATION:
            # Check if user has responded to script
            user_responded = ctx.session.state.get("user_responded_to_script", False)
            
            if not user_responded:
                # Check if we have user input to process
                user_feedback_raw = ctx.session.state.get(self.user_feedback.output_key)
                if user_feedback_raw:
                    # Process user feedback
                    async for event in self._run_sub_agent(self.user_feedback, ctx):
                        yield event
                    
                    # Extract user input from feedback
                    user_feedback_data = self._parse_json_response(user_feedback_raw, "user feedback")
                    if user_feedback_data:
                        user_input = user_feedback_data.get("user_input", "")
                        ctx.session.state["user_feedback"] = user_input
                        ctx.session.state["user_responded_to_script"] = True
                        
                        # Check if approved
                        if self._is_user_approval(user_input):
                            # Script approved, generate assets
                            ctx.session.state["workflow_stage"] = WorkflowStage.ASSET_GENERATION
                            yield text2event(self.name, "Script approved! Generating your YouTube Short...")
                            
                            yield text2event(self.name, "Creating visual prompts...")
                            async for event in self._run_sub_agent(self.prompt_generator, ctx):
                                yield event
                            
                            yield text2event(self.name, "Generating images...")
                            async for event in self.image_generator.run_async(ctx):
                                yield event
                            
                            yield text2event(
                                self.name,
                                f"YouTube Short creation complete! Check your project folder: {ctx.session.state.get('assets_path')}"
                            )
                            return
                        else:
                            # Script not approved, regenerate
                            yield text2event(self.name, "I'll revise the script based on your feedback...")
                            # Clear the old script and reset state
                            ctx.session.state.pop(self.script_writer.output_key, None)
                            ctx.session.state["user_responded_to_script"] = False
                            ctx.session.state["user_feedback"] = ""
                            async for event in self._draft_script_and_ask_for_feedback(ctx):
                                yield event
                            return
                else:
                    # No user feedback yet, show script again
                    async for event in self._draft_script_and_ask_for_feedback(ctx):
                        yield event
                    return

        # If we get here, something went wrong
        yield text2event(self.name, "Something went wrong. Please start over with a new request.")


# Create the main agent instance
youtube_shorts_creator_agent = YouTubeShortsCreatorAgent(
    name="YouTubeShortsCreatorAgent",
    theme_definer=theme_definer_agent,
    user_feedback=user_feedback_agent,
    researcher=researcher_agent,
    script_writer=script_writer_agent,
    prompt_generator=prompt_generator_agent,
)

root_agent = youtube_shorts_creator_agent 