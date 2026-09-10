# AGENTS.md

Single-file Flask weather dashboard (`app.py`). Weather from Open-Meteo — no API
key, `urllib` only. Run: `python3 app.py` → http://127.0.0.1:8000

## Tools

Use the most specific tool for the job.

**Code navigation — Serena, not grep:**

| Need | Tool |
|---|---|
| File structure (classes, functions, signatures) | `serena_get_symbols_overview` |
| One function or class | `serena_find_symbol` |
| All call sites | `serena_find_referencing_symbols` |
| Type/syntax errors without running anything | `serena_get_diagnostics_for_file` |

Call `serena_activate_project` **once per session** — don't re-activate before
each lookup. Never use `serena_replace_*` or `serena_insert_*`; edit with the
built-in `edit` tool instead.

**Reading docs — `webfetch`.** Fetch the page directly (e.g. Open-Meteo's API
docs). Don't open a browser to read documentation.

**Seeing the running app — `ego-browser`.** The only way to observe what you
actually built: load the page, read the rendered DOM, click through the UI.

Run it through `bash`:

```bash
ego-browser nodejs <<'EOF2'
const task = await useOrCreateTaskSpace('weather dashboard')
await openOrReuseTab('http://127.0.0.1:8000', { wait: true, timeout: 20 })
cliLog(await snapshotText())
EOF2
```

Available helpers — these are the only valid names:

`useOrCreateTaskSpace` `claimTaskSpace` `takeOverTaskSpace` `completeTaskSpace`
`openOrReuseTab` `listTabs` `switchTab` `closeTab` `pageInfo`
`snapshotText` `querySelector` `querySelectorAll`
`click` `fillInput` `typeText` `pressKey` `uploadFile`
`scroll` `scrollBy` `scrollToBottomUntil` `wait` `waitForAgentControl`
`cdp` `serverFetch` `cliLog` `help`

If one returns "Unknown helper", **do not guess synonyms** — that helper is
unavailable in this build. Use `snapshotText()` and `pageInfo()` to inspect the
page instead, and move on.

Start the server first and confirm it's up before opening a tab.

**`bash`** — running and verifying: `python3 app.py`, `python3 -m py_compile`,
`curl`, `git`. Never for reading, searching, or editing files.

## Editing

`edit` for existing files, `write` for new ones.

`oldString` must match byte for byte. Never write it from memory or from an
earlier version — `read` the target lines immediately before each edit and copy
it verbatim from that output. One logical change per call; a whole
`render_template_string` block will not match.

On "Could not find oldString":

1. Re-`read` the region (`offset`/`limit`), retry once from that fresh output.
2. Still failing — rewrite that section with `write`.
3. Never a third retry. Never `bash`/`sed`/heredocs to make the edit; rewriting
   through the shell corrupts the embedded HTML/CSS/JS.

## Verifying changes

Before reporting done:

1. `python3 -m py_compile app.py`
2. Extract the inline `<script>` and `node --check` it
3. Load the page in `ego-browser` and confirm it renders — check touched tags are
   balanced and CSS class names are ASCII-only (a stray non-ASCII character in a
   class name silently breaks styling)

## Constraints

- Flask is the only dependency. HTTP via `urllib`, not `requests`.
- HTML/CSS/JS live inline in `render_template_string` — no separate templates.
- Open-Meteo needs no key. Don't add auth or a key-based provider.
