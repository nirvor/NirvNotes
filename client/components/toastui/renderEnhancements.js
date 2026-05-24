import { mdiCheck, mdiContentCopy } from "@mdi/js";

const codeBlockWrapperClass = "flatnotes-code-block-wrapper";
const codeCopyButtonClass = "flatnotes-code-copy-button";
const copiedClass = "flatnotes-code-copy-button-copied";
const failedClass = "flatnotes-code-copy-button-failed";
const resetDelayMs = 1600;

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
