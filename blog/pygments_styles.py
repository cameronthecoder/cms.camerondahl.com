"""
GitHub Light syntax-highlighting style for Pygments.

Pygments ships `github-dark` but no light counterpart, so this mirrors that
style's token-to-role mapping (pygments/styles/gh_dark.py) with the light
colours from GitHub's Primer palette / github-vscode-theme "GitHub Light".
"""

from pygments.style import Style
from pygments.token import (
    Comment, Error, Generic, Keyword, Literal, Name, Number, Operator, String, Text, Token,
)

RED_5 = "#cf222e"        # keywords, operators
RED_8 = "#82071e"        # deleted-diff text
RED_0 = "#ffebe9"        # deleted-diff background
ORANGE_6 = "#953800"     # classes, exceptions, entities
GREEN_6 = "#116329"      # HTML/XML tags, inserted-diff text
GREEN_0 = "#dafbe1"      # inserted-diff background
BLUE_6 = "#0550ae"       # constants, properties, variables
BLUE_8 = "#0a3069"       # strings, numbers
PURPLE_5 = "#8250df"     # functions, decorators
GRAY_5 = "#6e7781"       # comments
GRAY_4 = "#8c959f"
FG_DEFAULT = "#1f2328"
# github.com's background for rendered code blocks (the editor theme itself
# uses #ffffff).
BG_DEFAULT = "#f6f8fa"


class GitHubLightStyle(Style):
    """GitHub's light colour scheme."""

    name = "github-light"

    background_color = BG_DEFAULT
    highlight_color = "#eaeef2"
    line_number_color = GRAY_4
    line_number_background_color = BG_DEFAULT
    line_number_special_color = FG_DEFAULT
    line_number_special_background_color = "#eaeef2"

    styles = {
        Token:              FG_DEFAULT,
        Error:              RED_5,

        Keyword:            RED_5,
        Keyword.Constant:   BLUE_6,
        Keyword.Pseudo:     BLUE_6,

        Name:               FG_DEFAULT,
        Name.Class:         "bold " + ORANGE_6,
        Name.Constant:      "bold " + BLUE_6,
        Name.Decorator:     "bold " + PURPLE_5,
        Name.Entity:        ORANGE_6,
        Name.Exception:     "bold " + ORANGE_6,
        Name.Function:      "bold " + PURPLE_5,
        Name.Label:         "bold " + BLUE_6,
        Name.Namespace:     RED_5,
        Name.Property:      BLUE_6,
        Name.Tag:           GREEN_6,
        Name.Variable:      BLUE_6,

        Literal:            BLUE_8,
        Literal.Date:       BLUE_6,
        String:             BLUE_8,
        String.Affix:       BLUE_6,
        String.Delimiter:   BLUE_6,
        String.Escape:      BLUE_6,
        String.Heredoc:     BLUE_6,
        String.Regex:       BLUE_6,
        Number:             BLUE_8,

        Comment:            "italic " + GRAY_5,
        Comment.Preproc:    "bold " + GRAY_5,
        Comment.Special:    "bold italic " + GRAY_5,

        Operator:           "bold " + RED_5,

        Generic:            FG_DEFAULT,
        Generic.Deleted:    f"bg:{RED_0} {RED_8}",
        Generic.Emph:       "italic",
        Generic.Error:      RED_5,
        Generic.Heading:    "bold " + BLUE_6,
        Generic.Inserted:   f"bg:{GREEN_0} {GREEN_6}",
        Generic.Output:     GRAY_5,
        Generic.Prompt:     GRAY_5,
        Generic.Strong:     "bold",
        Generic.EmphStrong: "bold italic",
        Generic.Subheading: BLUE_6,
        Generic.Traceback:  RED_5,
        Generic.Underline:  "underline",
        Text.Whitespace:    GRAY_4,
    }
