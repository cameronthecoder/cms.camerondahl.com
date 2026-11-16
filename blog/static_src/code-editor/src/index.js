// CodeMirror 6 editor for CodeBlock's `code` field in the Wagtail admin.
//
// Registered as the `code-editor` Stimulus controller on Wagtail's own app,
// so it attaches to StreamField blocks added after page load too. The
// textarea stays in the form (hidden) as the submitted value; CodeMirror
// writes every change back into it. Syntax highlighting follows the sibling
// `language` dropdown of the same CodeBlock.
//
// Rebuild after editing: `npm install && npm run build` in this directory.

import { EditorView, keymap, lineNumbers, highlightActiveLine, highlightActiveLineGutter, drawSelection } from '@codemirror/view';
import { EditorState, Compartment } from '@codemirror/state';
import { defaultKeymap, history, historyKeymap, indentWithTab } from '@codemirror/commands';
import {
  StreamLanguage,
  bracketMatching,
  defaultHighlightStyle,
  indentOnInput,
  indentUnit,
  syntaxHighlighting,
} from '@codemirror/language';
import { closeBrackets, closeBracketsKeymap } from '@codemirror/autocomplete';
import { python } from '@codemirror/lang-python';
import { javascript } from '@codemirror/lang-javascript';
import { html } from '@codemirror/lang-html';
import { css } from '@codemirror/lang-css';
import { java } from '@codemirror/lang-java';
import { cpp } from '@codemirror/lang-cpp';
import { go } from '@codemirror/lang-go';
import { php } from '@codemirror/lang-php';
import { csharp, kotlin } from '@codemirror/legacy-modes/mode/clike';
import { ruby } from '@codemirror/legacy-modes/mode/ruby';
import { swift } from '@codemirror/legacy-modes/mode/swift';

// Keys match CodeBlock.language's choices in blog/models.py.
const LANGUAGES = {
  py: python,
  js: javascript,
  html,
  css,
  java,
  csharp: () => StreamLanguage.define(csharp),
  cpp,
  ruby: () => StreamLanguage.define(ruby),
  go,
  php: () => php({ plain: true }),
  swift: () => StreamLanguage.define(swift),
  kotlin: () => StreamLanguage.define(kotlin),
};

const languageExtension = (key) => (LANGUAGES[key] ? LANGUAGES[key]() : []);

const theme = EditorView.theme({
  '&': {
    border: '1px solid var(--w-color-border-field-default, #9e9e9e)',
    borderRadius: '0.3125rem',
    backgroundColor: 'var(--w-color-surface-field, #fff)',
    color: 'var(--w-color-text-context, #262626)',
    fontSize: '0.875rem',
  },
  '&.cm-focused': {
    outline: '3px solid var(--w-color-focus, #00a885)',
    outlineOffset: '2px',
  },
  '.cm-scroller': {
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace',
    lineHeight: '1.5',
    minHeight: '9rem',
  },
  '.cm-content': { padding: '0.75rem 0' },
  '.cm-line': { padding: '0 0.75rem' },
  '.cm-gutters': {
    backgroundColor: 'var(--w-color-surface-page, #f6f6f8)',
    color: 'var(--w-color-text-placeholder, #767676)',
    borderRight: '1px solid var(--w-color-border-furniture, #e0e0e0)',
    borderRadius: '0.3125rem 0 0 0.3125rem',
  },
  '.cm-activeLine, .cm-activeLineGutter': {
    backgroundColor: 'color-mix(in srgb, var(--w-color-text-placeholder, #767676) 10%, transparent)',
  },
});

class CodeEditorController extends window.StimulusModule.Controller {
  connect() {
    const textarea = this.element;
    this.language = new Compartment();
    this.languageSelect = this.findLanguageSelect();

    this.view = new EditorView({
      parent: textarea.parentNode,
      state: EditorState.create({
        doc: textarea.value,
        extensions: [
          lineNumbers(),
          highlightActiveLineGutter(),
          highlightActiveLine(),
          drawSelection(),
          history(),
          indentOnInput(),
          bracketMatching(),
          closeBrackets(),
          indentUnit.of('    '),
          syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
          // Tab indents; Esc then Tab moves focus on (CodeMirror's built-in
          // escape hatch for keyboard users).
          keymap.of([...closeBracketsKeymap, ...defaultKeymap, ...historyKeymap, indentWithTab]),
          this.language.of(languageExtension(this.languageSelect?.value)),
          EditorView.contentAttributes.of({ 'aria-label': 'Code' }),
          EditorView.updateListener.of((update) => {
            if (!update.docChanged) return;
            textarea.value = update.state.doc.toString();
            // Lets Wagtail's unsaved-changes tracking notice the edit.
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
          }),
          theme,
        ],
      }),
    });
    textarea.after(this.view.dom);
    textarea.hidden = true;

    this.onLanguageChange = () => {
      this.view.dispatch({ effects: this.language.reconfigure(languageExtension(this.languageSelect.value)) });
    };
    this.languageSelect?.addEventListener('change', this.onLanguageChange);
  }

  disconnect() {
    this.languageSelect?.removeEventListener('change', this.onLanguageChange);
    this.view?.destroy();
    this.element.hidden = false;
  }

  // StructBlock child inputs share an id prefix: `<prefix>-code` and
  // `<prefix>-language`.
  findLanguageSelect() {
    const { id } = this.element;
    if (!id.endsWith('-code')) return null;
    return document.getElementById(`${id.slice(0, -'-code'.length)}-language`);
  }
}

window.wagtail.app.register('code-editor', CodeEditorController);
