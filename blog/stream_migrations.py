"""
StreamField data operations for blog migrations (used with Wagtail's
MigrateStreamData, which applies them to live pages and their revisions).

Kept in a module rather than in the migration file so they can be imported
by path when the migration is deconstructed.
"""

from django.utils.deconstruct import deconstructible
from wagtail.blocks.migrations.operations import BaseBlockOperation


@deconstructible
class MergeQuoteBlocksOperation(BaseBlockOperation):
    """Top-level stream op: `pull_quote` ({author, source}) and the old
    BlockQuoteBlock `quote` (a plain string) both become the QuoteBlock
    `quote` ({text, attribution, source_url}). Already-converted quotes are
    left alone, so it's safe to re-run."""

    def apply(self, block_value):
        converted = []
        for child in block_value:
            if child["type"] == "pull_quote":
                value = child.get("value") or {}
                child = {**child, "type": "quote", "value": {
                    "text": value.get("source") or "",
                    "attribution": value.get("author") or "",
                    "source_url": "",
                }}
            elif child["type"] == "quote" and not isinstance(child.get("value"), dict):
                child = {**child, "value": {
                    "text": child.get("value") or "",
                    "attribution": "",
                    "source_url": "",
                }}
            converted.append(child)
        return converted

    @property
    def operation_name_fragment(self):
        return "merge_quote_blocks"


@deconstructible
class ImageChooserToWritingImageOperation(BaseBlockOperation):
    """`image` block op: an ImageChooserBlock value (an image id) becomes a
    WritingImageBlock value, with the image's default alt text (description,
    else title) filled in. Already-converted values are left alone."""

    def apply(self, block_value):
        if isinstance(block_value, dict):
            return block_value
        return {
            "image": {
                "image": block_value,
                "alt_text": self._default_alt_text(block_value),
                "decorative": False,
            },
            "caption": "",
        }

    @staticmethod
    def _default_alt_text(image_id):
        from wagtail.images import get_image_model

        if image_id is None:
            return ""
        image = get_image_model().objects.filter(pk=image_id).first()
        return image.default_alt_text if image else ""

    @property
    def operation_name_fragment(self):
        return "image_chooser_to_writing_image"
