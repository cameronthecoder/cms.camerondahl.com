from django import forms


class CodeEditorWidget(forms.Textarea):
    """A textarea replaced by a CodeMirror 6 editor in the Wagtail admin.

    The editor is the `code-editor` Stimulus controller in
    blog/static/blog/code-editor.js, a bundle built from
    blog/static_src/code-editor (`npm install && npm run build` there). It
    registers on Wagtail's own Stimulus app, so it attaches to StreamField
    blocks added after page load too. Without JS this is a plain textarea.
    """

    def __init__(self, attrs=None):
        default_attrs = {
            'rows': 8,
            'data-controller': 'code-editor',
            'spellcheck': 'false',
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    class Media:
        js = ['blog/code-editor.js']
