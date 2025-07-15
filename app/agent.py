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
    SCRIPT_REFINEMENT = 2


class YouTubeShortsCreatorAgent(BaseAgent):
    """Orchestrates the YouTube Shorts creation workflow."""

    theme_definer: Agent
    user_feedback: Agent
    researcher: Agent
    script_writer: Agent
    prompt_generator: Agent
    workflow_stage: WorkflowStage = WorkflowStage.THEME_DEFINITION
    theme_approved: bool = False
    script_approved: bool = False

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

    async def _define_theme_and_ask_for_feedback(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Define theme and ask for user feedback."""
        yield text2event(self.name, "Let me analyze your request and propose a theme...")
        
        async for event in self._run_sub_agent(self.theme_definer, ctx):
            yield event

        theme_intent_raw = ctx.session.state.get(self.theme_definer.output_key)
        if theme_intent_raw:
            try:
                # Try to parse as JSON if it's a string
                if isinstance(theme_intent_raw, str):
                    theme_intent = json.loads(theme_intent_raw)
                else:
                    theme_intent = theme_intent_raw
                
                theme = theme_intent.get("theme", "Unknown Theme")
                intent = theme_intent.get("user_intent", "No intent specified")
            except (json.JSONDecodeError, AttributeError):
                # Fallback if JSON parsing fails
                theme = "Unknown Theme"
                intent = str(theme_intent_raw) if theme_intent_raw else "No intent specified"
            
            yield text2event(
                self.name,
                f"I propose this theme: **{theme}**\n\n"
                f"Intent: {intent}\n\n"
                f"Does this look good to you? Type 'yes' to approve or provide feedback for changes."
            )

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

        try:
            # Try to parse as JSON if it's a string
            if isinstance(theme_intent_raw, str):
                theme_intent = json.loads(theme_intent_raw)
            else:
                theme_intent = theme_intent_raw
            
            theme = theme_intent.get("theme", "default")
            intent = theme_intent.get("user_intent", "")
        except (json.JSONDecodeError, AttributeError):
            # Fallback if JSON parsing fails
            theme = "default"
            intent = str(theme_intent_raw) if theme_intent_raw else ""
        
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

        # Get workflow state from session or initialize
        workflow_stage = ctx.session.state.get("workflow_stage", WorkflowStage.THEME_DEFINITION)
        theme_approved = ctx.session.state.get("theme_approved", False)
        script_approved = ctx.session.state.get("script_approved", False)
        
        logger.info(f"[{self.name}] Workflow state: {workflow_stage}, Theme approved: {theme_approved}, Script approved: {script_approved}")

        if workflow_stage == WorkflowStage.THEME_DEFINITION:
            if not theme_approved:
                # Theme definition feedback loop
                async for event in self._define_theme_and_ask_for_feedback(ctx):
                    yield event
                return
            else:
                # Process user's feedback
                async for event in self._run_sub_agent(self.user_feedback, ctx):
                    yield event

                user_feedback_raw = ctx.session.state.get(self.user_feedback.output_key, {})
                try:
                    # Try to parse as JSON if it's a string
                    if isinstance(user_feedback_raw, str):
                        user_feedback = json.loads(user_feedback_raw)
                    else:
                        user_feedback = user_feedback_raw
                    
                    user_input = user_feedback.get("user_input", "")
                except (json.JSONDecodeError, AttributeError):
                    # Fallback if JSON parsing fails
                    user_input = str(user_feedback_raw) if user_feedback_raw else ""
                
                if user_input.lower() not in ["yes", "approve", "good", "perfect"]:
                    # Theme not approved, keep iterating
                    ctx.session.state["theme_approved"] = False
                    async for event in self._define_theme_and_ask_for_feedback(ctx):
                        yield event
                    return
                else:
                    # Theme approved, move to script refinement
                    ctx.session.state["theme_approved"] = True
                    ctx.session.state["workflow_stage"] = WorkflowStage.SCRIPT_REFINEMENT
                    yield text2event(self.name, "Theme approved! Moving to script creation...")

                    async for event in self._setup_assets_folder(ctx):
                        yield event

                    # Research phase
                    yield text2event(self.name, "Researching your topic...")
                    async for event in self._run_sub_agent(self.researcher, ctx):
                        yield event

                    # Script creation feedback loop
                    yield text2event(self.name, "Research complete! Creating your script...")
                    async for event in self._draft_script_and_ask_for_feedback(ctx):
                        yield event
                    return

        elif workflow_stage == WorkflowStage.SCRIPT_REFINEMENT:
            if not script_approved:
                # Script creation feedback loop
                async for event in self._draft_script_and_ask_for_feedback(ctx):
                    yield event
                return
            else:
                # Process user's feedback
                async for event in self._run_sub_agent(self.user_feedback, ctx):
                    yield event

            user_feedback_raw = ctx.session.state.get(self.user_feedback.output_key, {})
            try:
                # Try to parse as JSON if it's a string
                if isinstance(user_feedback_raw, str):
                    user_feedback = json.loads(user_feedback_raw)
                else:
                    user_feedback = user_feedback_raw
                
                user_input = user_feedback.get("user_input", "")
            except (json.JSONDecodeError, AttributeError):
                # Fallback if JSON parsing fails
                user_input = str(user_feedback_raw) if user_feedback_raw else ""

            if user_input.lower() not in ["yes", "approve", "good", "perfect"]:
                # Script not approved, keep iterating
                ctx.session.state["script_approved"] = False
                async for event in self._draft_script_and_ask_for_feedback(ctx):
                    yield event
                return
            else:
                # Script approved, generate assets
                ctx.session.state["script_approved"] = True
                yield text2event(self.name, "Script approved! Generating your YouTube Short...")

                # Generate image prompts
                yield text2event(self.name, "Creating visual prompts...")
                async for event in self._run_sub_agent(self.prompt_generator, ctx):
                    yield event

                # Generate images (run the custom agent manually)
                yield text2event(self.name, "Generating images...")
                async for event in self.image_generator.run_async(ctx):
                    yield event

                yield text2event(
                    self.name,
                    f"YouTube Short creation complete! Check your project folder: {ctx.session.state.get('assets_path')}"
                )

        return


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