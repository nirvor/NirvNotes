<template>
  <div class="flatnotes-html-editor">
    <div class="flatnotes-html-editor-toolbar">
      <NoteKindSwitch
        v-if="showKindSwitch"
        :current-kind="currentKind"
        @set-kind="setKind"
      />
      <div class="flatnotes-html-editor-toolbar-group">
        <span class="flatnotes-html-editor-label">HTML</span>
        <select
          v-model="selectedSnippet"
          class="flatnotes-html-editor-select"
          aria-label="HTML component"
        >
          <option
            v-for="snippet in htmlComponentSnippets"
            :key="snippet.id"
            :value="snippet.id"
          >
            {{ snippet.label }}
          </option>
        </select>
        <button type="button" @click="insertSelectedSnippet">Insert</button>
      </div>
      <div class="flatnotes-html-editor-toolbar-group">
        <button type="button" @click="chooseImage">Media</button>
      </div>
      <input
        ref="fileInput"
        type="file"
        accept="image/*"
        class="hidden"
        @change="imageChosen"
      />
    </div>
    <textarea
      ref="textarea"
      v-model="content"
      class="flatnotes-html-editor-source"
      rows="1"
      spellcheck="false"
      @input="contentInputHandler"
      @keydown="keydownHandler"
      @paste="pasteHandler"
      @drop="dropHandler"
      @dragover.prevent
    ></textarea>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref } from "vue";

import NoteKindSwitch from "../NoteKindSwitch.vue";
import {
  createMediaFigureSnippet,
  getHtmlSnippet,
  htmlComponentSnippets,
} from "./componentKit.js";

const props = defineProps({
  currentKind: {
    type: String,
    default: "research",
  },
  initialValue: String,
  addImageBlobHook: Function,
  showKindSwitch: Boolean,
});

const emit = defineEmits(["change", "keydown", "set-kind"]);

const content = ref(props.initialValue || "");
const fileInput = ref();
const selectedSnippet = ref(htmlComponentSnippets[0]?.id || "");
const textarea = ref();

function chooseImage() {
  fileInput.value?.click();
}

function setKind(kind) {
  emit("set-kind", kind);
}

function getSelectionText() {
  const element = textarea.value;
  if (!element) {
    return "";
  }

  return content.value.slice(element.selectionStart, element.selectionEnd);
}

function insertAtCursor(snippet) {
  const element = textarea.value;
  if (!element) {
    content.value += snippet;
    emit("change");
    nextTick(resizeTextarea);
    return;
  }

  const start = element.selectionStart;
  const end = element.selectionEnd;
  content.value = `${content.value.slice(0, start)}${snippet}${content.value.slice(end)}`;

  requestAnimationFrame(() => {
    const nextPosition = start + snippet.length;
    resizeTextarea();
    element.focus();
    element.setSelectionRange(nextPosition, nextPosition);
  });
  emit("change");
}

function resizeTextarea() {
  const element = textarea.value;
  if (!element) {
    return;
  }

  element.style.height = "auto";
  element.style.height = `${element.scrollHeight}px`;
}

function contentInputHandler() {
  resizeTextarea();
  emit("change");
}

function insertSelectedSnippet() {
  const snippet = getHtmlSnippet(selectedSnippet.value, getSelectionText());
  if (snippet) {
    insertAtCursor(snippet);
  }
}

function insertImageFile(file) {
  if (!file || !props.addImageBlobHook) {
    return;
  }

  props.addImageBlobHook(file, (url, altText, metadata = {}) => {
    insertAtCursor(createMediaFigureSnippet(url, altText, metadata));
  });
}

function imageChosen(event) {
  const [file] = event.target.files || [];
  event.target.value = "";
  insertImageFile(file);
}

function getImageFiles(dataTransfer) {
  return [...(dataTransfer?.files || [])].filter((file) =>
    file.type?.startsWith("image/"),
  );
}

function pasteHandler(event) {
  const [file] = getImageFiles(event.clipboardData);
  if (!file) {
    return;
  }

  event.preventDefault();
  insertImageFile(file);
}

function dropHandler(event) {
  const [file] = getImageFiles(event.dataTransfer);
  if (!file) {
    return;
  }

  event.preventDefault();
  insertImageFile(file);
}

function keydownHandler(event) {
  emit("keydown", event);
}

function getContent() {
  return content.value;
}

function isWysiwygMode() {
  return false;
}

onMounted(async () => {
  await nextTick();
  resizeTextarea();
  textarea.value?.focus();
});

defineExpose({ getContent, isWysiwygMode });
</script>

<style lang="scss" scoped>
.flatnotes-html-editor {
  display: flex;
  min-height: 65vh;
  flex-direction: column;
  border: 1px solid rgb(var(--theme-border));
  border-radius: 6px;
  overflow: visible;
  background-color: rgb(var(--theme-background));
}

.flatnotes-html-editor-toolbar {
  display: flex;
  min-height: 1.82rem;
  align-items: center;
  justify-content: flex-start;
  flex-wrap: wrap;
  gap: 0.28rem;
  padding: 0.16rem 0.5rem;
  border-bottom: 1px solid rgb(var(--theme-border));
  color: rgb(var(--theme-text-muted));
  background-color: rgb(var(--theme-background-elevated));
  font-size: 0.82rem;
  font-weight: 600;
}

.flatnotes-html-editor-toolbar-group {
  display: flex;
  align-items: center;
  gap: 0.32rem;
  min-width: 0;
}

.flatnotes-html-editor-label {
  flex: 0 0 auto;
}

.flatnotes-html-editor-select,
.flatnotes-html-editor-toolbar button {
  min-height: 1.42rem;
  border: 1px solid rgb(var(--theme-border));
  border-radius: 5px;
  padding: 0 0.45rem;
  color: rgb(var(--theme-text));
  background-color: rgb(var(--theme-background));
  font-size: 0.78rem;
  touch-action: manipulation;
}

.flatnotes-html-editor-select {
  min-width: min(11rem, 48vw);
  max-width: 100%;
  outline: none;
}

.flatnotes-html-editor-select:focus-visible,
.flatnotes-html-editor-toolbar button:hover,
.flatnotes-html-editor-toolbar button:focus-visible {
  border-color: rgb(var(--theme-brand));
}

.flatnotes-html-editor-source {
  min-height: 65vh;
  flex: 0 0 auto;
  resize: none;
  overflow-y: hidden;
  padding: 0.68rem 0.82rem;
  border: 0;
  color: rgb(var(--theme-text));
  background-color: rgb(var(--theme-background));
  font-family: Consolas, "Lucida Console", Monaco, "Andale Mono", monospace;
  font-size: 0.9rem;
  line-height: 1.45;
  outline: none;
  tab-size: 2;
}

@media (max-width: 640px) and (pointer: coarse), (max-width: 640px) and (hover: none) {
  .flatnotes-html-editor-toolbar {
    min-height: 2.35rem;
    gap: 0.4rem;
    padding: 0.26rem;
  }

  .flatnotes-html-editor-toolbar-group {
    gap: 0.45rem;
  }

  .flatnotes-html-editor-select,
  .flatnotes-html-editor-toolbar button {
    min-height: 2rem;
    padding: 0 0.65rem;
  }
}
</style>
