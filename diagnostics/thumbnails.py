"""Small previews of screenshots for the report list"""

from pathlib import Path

from PIL import Image

from .models import Attachment

THUMBNAIL_SIZE = (480, 270)


def get_thumbnail(attachment: Attachment) -> Path | None:
    """Find or generate a thumbnail for a given attachment"""
    thumbnail = attachment.thumbnail_path
    if thumbnail.exists():
        return thumbnail

    try:
        with Image.open(attachment.path) as image:
            image.thumbnail(THUMBNAIL_SIZE)
            thumbnail.parent.mkdir(parents=True, exist_ok=True)
            image.convert("RGB").save(thumbnail, "JPEG", quality=80)
    except (OSError, ValueError, Image.DecompressionBombError):
        # Missing, still uploading, or otherwise invalid
        return None

    return thumbnail
