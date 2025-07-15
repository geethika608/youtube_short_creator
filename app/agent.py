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
    """Orchestrates the YouTube Shorts creation workflow, including user approval steps."""

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
        image_generator: Agent,
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
        # Store image_generator as a regular attribute since it's a custom agent
        self.image_generator = image_generator

    async def _run_sub_agent(
        self, agent: BaseAgent, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Run a sub-agent and yield its events."""
        logger.info(f"[{self.name}] Running {agent.name}...")

        async for event in agent.run_async(ctx):
            yield event

        agent_output = ctx.session.state.get(agent.output_key)
        if not agent_output:
            error_msg = f"[{self.name}] {agent.name} did not produce '{agent.output_key}' in session state. Aborting workflow."
            logger.error(error_msg)
            yield text2event(self.name, error_msg)
            return

        logger.info(f"[{self.name}] {agent.name} completed. Output: {agent_output}")

    async def _define_theme_and_ask_for_feedback(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Define theme and ask for user feedback."""
        # 1. Define Theme
        async for event in self._run_sub_agent(self.theme_definer, ctx):
            yield event

        # 2. Ask for user feedback
        theme_intent = ctx.session.state[self.theme_definer.output_key]
        theme = theme_intent["theme"]
        yield text2event(
            self.name,
            f"It seems that you want to create a short video content about '{theme}' is this correct?\n\nAnswer with 'yes' or describe what theme you want.",
        )

        self.theme_approved = True

    async def _draft_script_and_ask_for_feedback(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Draft script and ask for user feedback."""
        # 1. Script creation
        async for event in self._run_sub_agent(self.script_writer, ctx):
            yield event

        ctx.session.state["current_script"] = ctx.session.state.get(
            self.script_writer.output_key
        )

        # 2. Ask for user feedback
        yield text2event(
            self.name,
            f"Here's your script:\n\n**{ctx.session.state['current_script']}**\n\n"
            f"Does this script work for you? Type 'yes' to approve or provide feedback for changes.",
        )

    async def _setup_assets_folder(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Set up the assets folder for the project."""
        theme_intent = ctx.session.state[self.theme_definer.output_key]
        theme = theme_intent["theme"]
        intent = theme_intent["user_intent"]
        
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

        if self.workflow_stage == WorkflowStage.THEME_DEFINITION:
            if not self.theme_approved:
                # 1. Theme definition feedback loop
                async for event in self._define_theme_and_ask_for_feedback(ctx):
                    yield event
                return
            else:
                # 1.1. Process user's feedback
                async for event in self._run_sub_agent(self.user_feedback, ctx):
                    yield event

                user_input = ctx.session.state.get(self.user_feedback.output_key).get(
                    self.user_feedback.output_key
                )

                # Theme not approved
                if user_input.lower() != "approved":
                    # 1.2. If not approved keep iterating
                    self.theme_approved = False
                    async for event in self._define_theme_and_ask_for_feedback(ctx):
                        yield event
                    return
                # Theme approved
                else:
                    self.workflow_stage = WorkflowStage.SCRIPT_REFINEMENT
                    yield text2event(
                        self.name, "Theme approved moving to script refinement stage"
                    )

                    async for event in self._setup_assets_folder(ctx):
                        yield event

                    # 2. Research
                    yield text2event(self.name, "Starting research...")
                    async for event in self._run_sub_agent(self.researcher, ctx):
                        yield event

                    # 3. Script creation feedback loop
                    yield text2event(
                        self.name, "Research finished, starting script creation"
                    )
                    async for event in self._draft_script_and_ask_for_feedback(ctx):
                        yield event
                    return

        elif self.workflow_stage == WorkflowStage.SCRIPT_REFINEMENT:
            # This needs to be reset
            async for event in self._setup_assets_folder(ctx):
                yield event

            # 3.1. Process user's feedback
            async for event in self._run_sub_agent(self.user_feedback, ctx):
                yield event

            user_input = ctx.session.state.get(self.user_feedback.output_key).get(
                self.user_feedback.output_key
            )

            # Script not approved
            if user_input.lower() != "approved":
                # 3.2. If not approved keep iterating
                self.script_approved = False
                async for event in self._draft_script_and_ask_for_feedback(ctx):
                    yield event
                return
            # Script approved
            else:
                yield text2event(
                    self.name, "Script approved, starting the asset generation process."
                )

                # 4. Prompt generation
                yield text2event(self.name, "Generating prompts for the images...")
                async for event in self._run_sub_agent(self.prompt_generator, ctx):
                    yield event

                # 5. Image generation
                yield text2event(self.name, "Generating images...")
                async for event in self.image_generator.run_async(ctx):
                    yield event

                yield text2event(
                    self.name,
                    f"YouTube Short creation workflow finished. Assets stored at: '{ctx.session.state['assets_path']}'.",
                )

                logger.info(
                    f"\n\n[{self.name}] Finishing YouTube Shorts creation workflow.\n\n"
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
    image_generator=image_generator_agent,
)

root_agent = youtube_shorts_creator_agent 