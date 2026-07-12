import assert from "node:assert/strict";
import test from "node:test";

import {
  documentHasSystemTag,
  getFlatnotesMetaTags,
  setDocumentSystemTag,
} from "./noteSystemTags.js";

const researchNote = `<!doctype html>
<html><head><meta name="flatnotes-tags" content="private,research"></head>
<body><article><h1>Test</h1><p>#private #research #pinned</p></article></body></html>`;

test("pin state migrates from visible tag to metadata", () => {
  assert.equal(documentHasSystemTag(researchNote, "pinned", "html"), true);
  const pinned = setDocumentSystemTag({
    content: researchNote,
    title: "Test",
    format: "html",
    enabled: true,
  });
  assert.deepEqual(getFlatnotesMetaTags(pinned), [
    "private",
    "research",
    "pinned",
  ]);
  assert.doesNotMatch(pinned, /<p>#private #research #pinned<\/p>/);
  assert.match(pinned, /<p>#private #research<\/p>/);

  const unpinned = setDocumentSystemTag({
    content: pinned,
    title: "Test",
    format: "html",
    enabled: false,
  });
  assert.equal(documentHasSystemTag(unpinned, "pinned", "html"), false);
  assert.deepEqual(getFlatnotesMetaTags(unpinned), ["private", "research"]);
});

test("legacy markdown can still be pinned", () => {
  const pinned = setDocumentSystemTag({
    content: "# Title\n\nText\n",
    format: "markdown",
    enabled: true,
  });
  assert.match(pinned, /#pinned\n$/);
  const unpinned = setDocumentSystemTag({
    content: pinned,
    format: "markdown",
    enabled: false,
  });
  assert.doesNotMatch(unpinned, /#pinned/);
});
