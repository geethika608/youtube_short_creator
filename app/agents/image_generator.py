import logging
from pathlib import Path
from typing import Any, AsyncGenerator

from google import genai
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from pydantic import Field
from typing_extensions import override

from app.utils.genai_utils import get_client, text2event
from app.utils.image_utils import save_image_from_bytes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_ID = "models/imagen-3.0-generate-002"
ASPECT_RATIO = "9:16"


class ImagenAgent(BaseAgent):
    """An ADK Custom Agent that generates images using Imagen for YouTube Shorts."""

    client: genai.Client = None
    image_gen_config: dict = None

    # Configuration fields
    name: str = Field(default="ImageGeneratorAgent", description="The name of the agent")
    description: str = Field(
        default="Generates images for YouTube Shorts using Imagen",
        description="The description of the agent"
    )
    input_key: str = Field(
        default="image_prompts",
        description="The key in session state holding image prompts"
    )
    output_key: str = Field(
        default="images_path",
        description="The key to store generated image paths"
    )
    model: str = Field(default=MODEL_ID, description="The Imagen model to use")
    aspect_ratio: str = Field(default=ASPECT_RATIO, description="Aspect ratio for images")

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, **kwargs: Any):
        """Initialize the ImagenAgent."""
        super().__init__(**kwargs)
        self.client = None  # Initialize lazily
        self.image_gen_config = {
            "number_of_images": 1,
            "output_mime_type": "image/jpeg",
            "person_generation": "ALLOW_ADULT",
            "aspect_ratio": self.aspect_ratio,
        }
    
    def _get_client(self):
        """Get the client, initializing it if necessary."""
        if self.client is None:
            self.client = get_client()
        return self.client

    async def _generate_image(
        self, scene_idx: int, prompt: str, output_dir: Path
    ) -> AsyncGenerator[Event, None]:
        """Generate and save an image for a scene."""
        logger.info(f"[{self.name}] Generating image for scene {scene_idx + 1}")
        yield text2event(self.name, f"Generating image for scene {scene_idx + 1}...")

        try:
            client = self._get_client()
            result = client.models.generate_images(
                model=self.model, prompt=prompt, config=self.image_gen_config
            )

            if not result.generated_images:
                error_msg = f"Image generation failed for scene {scene_idx + 1}"
                logger.error(f"[{self.name}] {error_msg}")
                yield text2event(self.name, error_msg)
                return

            for image_idx, generated_image in enumerate(result.generated_images):
                image_bytes = generated_image.image.image_bytes
                img_filename = f"image_{image_idx + 1}.jpg"
                output_filepath = output_dir / img_filename
                save_image_from_bytes(image_bytes, output_filepath)

                logger.info(f"[{self.name}] Image saved to '{output_filepath}'")
                yield text2event(self.name, f"Image generated and saved!")

        except Exception as e:
            error_msg = f"Error generating image: {e}"
            logger.error(f"[{self.name}] {error_msg}")
            yield text2event(self.name, error_msg)

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Generate images for all prompts in session state."""
        logger.info(f"[{self.name}] Starting image generation")

        assets_path = Path(ctx.session.state.get("assets_path"))
        prompts_raw = ctx.session.state.get(self.input_key)
        
        # Handle different prompt formats
        if isinstance(prompts_raw, str):
            # If it's a string, split by lines
            prompts = [line.strip() for line in prompts_raw.split('\n') if line.strip()]
        elif isinstance(prompts_raw, list):
            prompts = prompts_raw
        elif isinstance(prompts_raw, dict) and self.input_key in prompts_raw:
            prompts = prompts_raw[self.input_key]
        else:
            prompts = []

        if not prompts:
            error_msg = f"No image prompts found in session state. Raw data: {prompts_raw}"
            logger.error(f"[{self.name}] {error_msg}")
            yield text2event(self.name, error_msg)
            return

        try:
            ctx.session.state[self.output_key] = []
            for scene_idx, prompt in enumerate(prompts):
                output_dir = assets_path / f"scene_{scene_idx + 1}" / "images"
                output_dir.mkdir(parents=True, exist_ok=True)
                ctx.session.state[self.output_key].append(str(output_dir))

                async for event in self._generate_image(scene_idx, prompt, output_dir):
                    yield event

            yield text2event(self.name, "All images generated successfully!")

        except Exception as e:
            error_msg = f"Error during image generation: {e}"
            logger.error(f"[{self.name}] {error_msg}")
            yield text2event(self.name, error_msg)


image_generator_agent = ImagenAgent(
    name="ImageGeneratorAgent",
    description="Generates images for YouTube Shorts using Imagen",
    input_key="image_prompts",
    output_key="images_path",
    model=MODEL_ID,
    aspect_ratio=ASPECT_RATIO,
) 