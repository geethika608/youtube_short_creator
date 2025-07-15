from pathlib import Path

from PIL import Image
import io


def save_image_from_bytes(image_bytes: bytes, output_path: Path) -> None:
    """Saves an image from bytes to a file.

    Args:
        image_bytes: The image data as bytes.
        output_path: The path where the image should be saved.
    """
    image = Image.open(io.BytesIO(image_bytes))
    image.save(output_path) 