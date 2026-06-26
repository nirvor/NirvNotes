# NirvNotes

NirvNotes is a private, HTML-first note system built on the useful foundation of
flatnotes, but now moving as its own app.

The core idea stays deliberately simple: one flat folder of notes, no notebook
tree, sparse bottom tags, fast search, and notes that remain easy for humans and
LLMs to read. The current fork focuses on clean HTML notes, media-rich research
notes, compact work notes, mobile-friendly viewing, and a calm dark interface.

## Current Direction

- One note file per note, currently HTML as the durable format.
- All active notes live in one folder and are organized through tags.
- Research notes can use clean sections, diagrams, plots, maps, images, source
  lists, and compact lead visuals.
- Work notes keep a rendered HTML view plus a raw Markdown copy source inside
  the same HTML note.
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
