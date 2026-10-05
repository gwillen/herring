# Development notes (claude-notes/ convention)

This repo keeps development notes in the `claude-notes/` directory:

- `claude-notes/_global.md` — always-relevant notes, imported below.
- `claude-notes/_index.md` — index of topic files, imported below. Read a topic file whenever its index line says it's relevant to the work at hand; read it in full before editing it.
- `claude-notes/*.md` — detailed notes, loaded on demand.

When recording new durable knowledge: put it in the matching topic file (or create a new one and add an index line), keep `_global.md` and `_index.md` terse, and prefer updating existing notes over duplicating them. This rules file exists because CLAUDE.md is reserved for manual editing.

As a general rule, do not use the memory files mechanism provided by the Claude Code harness; use `claude-notes/` instead, since `claude-notes/` is checked into the project's git repo and memory files are not.

The `_global.md` and `_index.md` files are always included in the context, using the relative path imports below. As with any files, if you edit them during the session, the copies at the beginning of the context will become stale; your latest tool outputs will have the latest contents.

@../../claude-notes/_global.md
@../../claude-notes/_index.md
