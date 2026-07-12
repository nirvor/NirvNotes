# NirvNotes

NirvNotes is a private, HTML-first note system built on the useful foundation of
flatnotes, but now moving as its own app.

The core idea stays deliberately simple: local project files remain local, while
selected durable notes live in one flat HTML library. There is no notebook tree,
no automatic import, and no second sync system. NirvNotes focuses on fast text
editing, sparse tags, media-rich research notes, mobile-friendly reading, and a
calm dark interface.

## Current Direction

- Workspace files (`.md`, `.txt`, `.cfg`, `.ini`) are edited in place at their
  original local path.
- Library notes are durable HTML files in one VPS folder and are organized
  through sparse content tags.
- `Keep as note` creates an explicit one-way HTML snapshot of a local file.
- The star controls favorites as hidden `pinned` metadata; users do not need to
  type `#pinned`.
- Research notes can use clean sections, diagrams, plots, maps, images, source
  lists, and compact lead visuals.
- Lightweight Library notes keep a rendered HTML view plus raw Markdown copy
  source inside the same HTML file.
- The app should stay quiet, fast, readable, and not turn into a dashboard-heavy
  knowledge base.

## Compatibility

Some internal names still use the original `flatnotes` namespace for stability:
CSS classes, note metadata such as `data-flatnotes-*`, and deployment
environment variables such as `FLATNOTES_PATH`. These are compatibility
surfaces, not the product name.

The user-facing product name is `NirvNotes`.

## Development

```shell
npm install
npm run build
```

The live VPS deployment is managed outside this README by the local flatnotes VPS
workspace scripts and Docker Compose setup.

## Upstream

NirvNotes started as a fork of the open-source flatnotes project by Adam
Dullage. The fork now carries substantial local HTML-note, media, workflow, and
UI changes.
