import { mdiCheck, mdiContentCopy } from "@mdi/js";
import katex from "katex";

const codeBlockWrapperClass = "flatnotes-code-block-wrapper";
const codeCopyButtonClass = "flatnotes-code-copy-button";
const copiedClass = "flatnotes-code-copy-button-copied";
const failedClass = "flatnotes-code-copy-button-failed";
const inlineLatexClass = "flatnotes-inline-latex";
const resetDelayMs = 1600;
const maxInlineLatexLength = 500;
const ignoredLatexSelector = [
  "a",
  "code",
  "kbd",
  "pre",
  "samp",
  "script",
  "style",
  "textarea",
  ".flatnotes-code-block-wrapper",
  ".katex",
].join(",");

const latexMacros = {
  "\\abs": "\\left\\lvert #1 \\right\\rvert",
  "\\bqty": "\\left[ #1 \\right]",
  "\\bra": "\\left\\langle #1 \\right|",
  "\\braket": "\\left\\langle #1 \\middle| #2 \\right\\rangle",
  "\\Bqty": "\\left\\lbrace #1 \\right\\rbrace",
  "\\curl": "\\nabla\\times",
  "\\dd": "\\,\\mathrm{d}",
  "\\divergence": "\\nabla\\cdot",
  "\\dv": "\\frac{\\mathrm{d} #1}{\\mathrm{d} #2}",
  "\\eval": "\\left. #1 \\right|_{#2}",
  "\\grad": "\\nabla",
  "\\ket": "\\left| #1 \\right\\rangle",
  "\\norm": "\\left\\lVert #1 \\right\\rVert",
  "\\num": "#1",
  "\\per": "\\,/",
  "\\pdv": "\\frac{\\partial #1}{\\partial #2}",
  "\\pqty": "\\left( #1 \\right)",
  "\\qty": "#1\\,#2",
  "\\si": "\\mathrm{#1}",
  "\\unit": "\\,\\mathrm{#1}",
  "\\va": "\\vec{#1}",
  "\\vb": "\\mathbf{#1}",
  "\\vu": "\\hat{\\mathbf{#1}}",
  "\\vqty": "\\left\\lvert #1 \\right\\rvert",
  "\\ampere": "\\mathrm{A}",
  "\\celsius": "^{\\circ}\\mathrm{C}",
  "\\electronvolt": "\\mathrm{eV}",
  "\\hertz": "\\mathrm{Hz}",
  "\\joule": "\\mathrm{J}",
  "\\kilogram": "\\mathrm{kg}",
  "\\meter": "\\mathrm{m}",
  "\\newton": "\\mathrm{N}",
  "\\ohm": "\\Omega",
  "\\second": "\\mathrm{s}",
  "\\tesla": "\\mathrm{T}",
  "\\volt": "\\mathrm{V}",
  "\\watt": "\\mathrm{W}",
};

const latexRenderOptions = {
  displayMode: false,
  macros: latexMacros,
  strict: "ignore",
  throwOnError: true,
  trust: false,
};

function createIcon(path) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");

  const iconPath = document.createElementNS(
    "http://www.w3.org/2000/svg",
    "path",
  );
  iconPath.setAttribute("d", path);
  svg.append(iconPath);

  return svg;
}

function setButtonState(button, state) {
  button.classList.remove(copiedClass, failedClass);
  button.replaceChildren(
    createIcon(state === "copied" ? mdiCheck : mdiContentCopy),
  );

  if (state === "copied") {
    button.classList.add(copiedClass);
    button.setAttribute("aria-label", "Code copied");
    button.setAttribute("title", "Code copied");
    return;
  }

  if (state === "failed") {
    button.classList.add(failedClass);
    button.setAttribute("aria-label", "Copy failed");
    button.setAttribute("title", "Copy failed");
    return;
  }

  button.setAttribute("aria-label", "Copy code");
  button.setAttribute("title", "Copy code");
}

function writeTextViaTextarea(text) {
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  textarea.style.pointerEvents = "none";
  document.body.append(textarea);
  textarea.select();

  try {
    if (!document.execCommand("copy")) {
      throw new Error("Copy command was not accepted by the browser.");
    }
  } finally {
    textarea.remove();
  }
}

async function writeClipboardText(text) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return;
    } catch {
      // Some browser contexts expose the Clipboard API but reject writes.
      // The textarea path keeps the button useful instead of failing early.
    }
  }

  writeTextViaTextarea(text);
}

function getCodeText(preElement) {
  const codeElement = preElement.querySelector("code");
  return codeElement ? codeElement.textContent : preElement.textContent;
}

function decorateCodeBlock(preElement) {
  if (preElement.closest(`.${codeBlockWrapperClass}`)) {
    return;
  }

  const wrapper = document.createElement("div");
  wrapper.className = codeBlockWrapperClass;
  preElement.parentNode.insertBefore(wrapper, preElement);
  wrapper.append(preElement);

  const button = document.createElement("button");
  button.type = "button";
  button.className = codeCopyButtonClass;
  setButtonState(button);

  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      await writeClipboardText(getCodeText(preElement));
      setButtonState(button, "copied");
    } catch {
      setButtonState(button, "failed");
    } finally {
      window.setTimeout(() => {
        setButtonState(button);
        button.disabled = false;
      }, resetDelayMs);
    }
  });

  wrapper.append(button);
}

export function enhanceCodeBlocks(rootElement) {
  if (!rootElement) {
    return;
  }

  rootElement
    .querySelectorAll(".toastui-editor-contents pre")
    .forEach(decorateCodeBlock);
}

function isEscaped(text, index) {
  let slashCount = 0;
  for (
    let cursor = index - 1;
    cursor >= 0 && text[cursor] === "\\";
    cursor -= 1
  ) {
    slashCount += 1;
  }

  return slashCount % 2 === 1;
}

function findClosingDollar(text, openingIndex) {
  for (
    let cursor = openingIndex + 1;
    cursor < text.length && cursor - openingIndex <= maxInlineLatexLength;
    cursor += 1
  ) {
    if (text[cursor] === "\n" || text[cursor] === "\r") {
      return -1;
    }

    if (text[cursor] === "$" && !isEscaped(text, cursor)) {
      return cursor;
    }
  }

  return -1;
}

function parseInlineLatexSegments(text) {
  const segments = [];
  let cursor = 0;

  while (cursor < text.length) {
    const openingIndex = text.indexOf("$", cursor);
    if (openingIndex === -1) {
      break;
    }

    const nextCharacter = text[openingIndex + 1];
    if (
      isEscaped(text, openingIndex) ||
      nextCharacter === "$" ||
      nextCharacter === undefined ||
      /\s/.test(nextCharacter)
    ) {
      cursor = openingIndex + 1;
      continue;
    }

    const closingIndex = findClosingDollar(text, openingIndex);
    if (closingIndex === -1) {
      break;
    }

    const latexSource = text.slice(openingIndex + 1, closingIndex);
    const previousCharacter = text[closingIndex - 1];
    if (!latexSource || /\s/.test(previousCharacter)) {
      cursor = openingIndex + 1;
      continue;
    }

    segments.push({
      end: closingIndex + 1,
      latexSource,
      start: openingIndex,
    });
    cursor = closingIndex + 1;
  }

  return segments;
}

function shouldSkipLatexTextNode(textNode) {
  const parentElement = textNode.parentElement;
  return !parentElement || parentElement.closest(ignoredLatexSelector);
}

function renderInlineLatex(latexSource) {
  const wrapper = document.createElement("span");
  wrapper.className = inlineLatexClass;
  wrapper.setAttribute("data-latex-source", latexSource);

  try {
    wrapper.innerHTML = katex.renderToString(latexSource, latexRenderOptions);
  } catch {
    return null;
  }

  return wrapper;
}

function replaceTextNodeWithInlineLatex(textNode) {
  const text = textNode.textContent;
  const segments = parseInlineLatexSegments(text);
  if (segments.length === 0) {
    return;
  }

  const fragment = document.createDocumentFragment();
  let cursor = 0;

  segments.forEach(({ end, latexSource, start }) => {
    if (start > cursor) {
      fragment.append(document.createTextNode(text.slice(cursor, start)));
    }

    const renderedLatex = renderInlineLatex(latexSource);
    fragment.append(
      renderedLatex || document.createTextNode(text.slice(start, end)),
    );
    cursor = end;
  });

  if (cursor < text.length) {
    fragment.append(document.createTextNode(text.slice(cursor)));
  }

  textNode.parentNode.replaceChild(fragment, textNode);
}

export function enhanceInlineLatex(rootElement) {
  if (!rootElement) {
    return;
  }

  const contentRoot = rootElement.querySelector(".toastui-editor-contents");
  if (!contentRoot) {
    return;
  }

  const textNodes = [];
  const walker = document.createTreeWalker(contentRoot, NodeFilter.SHOW_TEXT, {
    acceptNode(textNode) {
      if (
        shouldSkipLatexTextNode(textNode) ||
        !textNode.textContent.includes("$") ||
        parseInlineLatexSegments(textNode.textContent).length === 0
      ) {
        return NodeFilter.FILTER_REJECT;
      }

      return NodeFilter.FILTER_ACCEPT;
    },
  });

  while (walker.nextNode()) {
    textNodes.push(walker.currentNode);
  }

  textNodes.forEach(replaceTextNodeWithInlineLatex);
}

export function enhanceRenderedMarkdown(rootElement) {
  enhanceInlineLatex(rootElement);
  enhanceCodeBlocks(rootElement);
}
