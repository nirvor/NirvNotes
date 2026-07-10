<template>
  <section
    class="flatnotes-open-file min-w-0 max-w-full"
    @dblclick="openFileDblClickHandler"
    @pointerup="openFilePointerUpHandler"
  >
    <div class="flatnotes-open-file-heading">
      <div class="min-w-0">
        <div class="flatnotes-open-file-kicker-line">
          <span class="flatnotes-open-file-kicker">External File</span>
          <span
            v-for="item in metadataItems"
            :key="item.label"
            class="flatnotes-open-file-meta"
          >
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </span>
        </div>
        <h1 class="flatnotes-open-file-title">
          {{ activeFile ? activeFile.name : "Open a local file" }}
        </h1>
      </div>
    </div>

    <input
      ref="fileInput"
      type="file"
      class="hidden"
      accept=".md,.txt,.cfg,.ini,text/markdown,text/plain"
      multiple
      @change="fileInputChanged"
    />

    <div v-if="visibleStatusMessage" class="flatnotes-open-file-strip">
      <span
        class="flatnotes-open-file-status"
        :class="{ 'flatnotes-open-file-status-error': statusTone === 'error' }"
      >
        <SvgIcon type="mdi" :path="statusIcon" size="0.76rem" />
        {{ visibleStatusMessage }}
      </span>
    </div>

    <div
      v-if="files.length > 1"
      class="mb-3 flex flex-wrap gap-1.5 print:hidden"
    >
      <button
        v-for="file in files"
        :key="file.key"
        type="button"
        class="rounded-full border border-theme-border px-2 py-0.5 text-xs hover:border-theme-brand hover:text-theme-brand"
        :class="{
          'border-theme-brand text-theme-brand': activeFile?.key === file.key,
        }"
        @click="activateFile(file.key)"
      >
        {{ file.name }}
      </button>
    </div>

    <textarea
      v-if="activeFile && editMode"
      ref="editorTextarea"
      v-model="activeFile.draftContent"
      class="flatnotes-open-file-editor"
      spellcheck="false"
      @input="markActiveFileDirty"
      @keydown="documentKeydownHandler"
    ></textarea>

    <pre
      v-else-if="activeFile && activeFile.previewMode === 'plain'"
      class="flatnotes-open-file-plain-preview"
      >{{ activeFile.draftContent }}</pre
    >

    <ToastViewer
      v-else-if="activeFile"
      :key="activeFile.key"
      :initialValue="activeFile.previewMarkdown"
      :enhance-note-lead="false"
      :note-title="noteTitleForFile(activeFile)"
      class="toast-viewer min-w-0 max-w-full pb-4"
    />

    <div
      v-if="!activeFile"
      class="rounded-md border border-dashed border-theme-border px-3 py-4 text-center text-sm text-theme-text-muted"
    >
      <IconLabel
        :iconPath="mdiFileDocumentOutline"
        iconSize="1.35rem"
        class="mb-2 justify-center"
      />
      <p>
        Open a .md, .txt, .cfg, or .ini file through Windows, or choose one
        here. Nothing is saved into NirvNotes.
      </p>
    </div>
  </section>
</template>

<script setup>
import SvgIcon from "@jamescoyle/vue-icon";
import {
  mdiAlertCircleOutline,
  mdiCheck,
  mdiCheckCircleOutline,
  mdiClose,
  mdiContentSaveOutline,
  mdiContentCopy,
  mdiFileDocumentOutline,
  mdiFolderOpenOutline,
  mdiPencilOutline,
} from "@mdi/js";
import {
  computed,
  defineAsyncComponent,
  onMounted,
  onUnmounted,
  ref,
  watch,
  watchEffect,
} from "vue";
import { useRouter } from "vue-router";

import IconLabel from "../components/IconLabel.vue";
import { useDocumentSession } from "../documents/documentSession.js";
import { createLocalFileStorageAdapter } from "../documents/storageAdapters.js";
import {
  externalFileLaunch,
  supportsFileHandlingLaunchQueue,
  supportsNativeFileBridge,
} from "../externalFiles.js";
import { useGlobalStore } from "../globalStore.js";

const ToastViewer = defineAsyncComponent(
  () => import("../components/toastui/ToastViewer.vue"),
);

const editorTextarea = ref();
const fileInput = ref();
const files = ref([]);
const activeKey = ref(null);
const lastConsumedLaunchId = ref(null);
const statusMessage = ref("");
const statusTone = ref("info");
const router = useRouter();
const globalStore = useGlobalStore();
const localFileStorageAdapter = createLocalFileStorageAdapter();

const activeFile = computed(
  () => files.value.find((file) => file.key === activeKey.value) || null,
);
const documentSession = useDocumentSession({
  canEdit: () => Boolean(activeFile.value),
  hasDocument: () => Boolean(activeFile.value),
  requestClose: finishEditing,
  focusEditor: () => editorTextarea.value?.focus({ preventScroll: true }),
  beforeLeaveEdit: () => {
    if (activeFile.value) {
      refreshPreview(activeFile.value);
    }
  },
  draftKey: () => activeFile.value?.draftStorageKey || "",
  persistDraft: true,
  saveDocument: persistActiveFile,
  copyDocument: getActiveFileCopyPayload,
  afterSave: () => showStatus("Saved to original file."),
  onSaveError: handleActiveFileSaveError,
  afterCopy: () => showStatus("Copied raw source to clipboard."),
  onCopyError: () => showStatus("Could not copy this file.", "error"),
});
const editMode = documentSession.editMode;
const copied = documentSession.copied;
const openFileDblClickHandler = documentSession.contentDblClickHandler;
const openFilePointerUpHandler = documentSession.contentPointerUpHandler;
const canSaveActiveFile = computed(
  () =>
    Boolean(activeFile.value?.handle) &&
    Boolean(activeFile.value?.dirty) &&
    !documentSession.saving.value,
);
const metadataItems = computed(() => {
  if (!activeFile.value) {
    return [];
  }

  return [
    { label: "type", value: activeFile.value.extension || "text" },
    { label: "size", value: formatBytes(activeFile.value.size) },
  ];
});
const visibleStatusMessage = computed(() =>
  statusTone.value === "error" ? statusMessage.value : "",
);
const statusIcon = computed(() =>
  statusTone.value === "error" ? mdiAlertCircleOutline : mdiCheckCircleOutline,
);
onMounted(() => {
  if (!supportsFileHandlingLaunchQueue() && !supportsNativeFileBridge()) {
    showStatus(
      "This browser can preview files here, but Windows file opening needs the installed NirvNotes app.",
    );
  }
});

watch(externalFileLaunch, consumeExternalLaunch, { immediate: true });
watchEffect(updateOpenFileActions);

onUnmounted(() => globalStore.clearNoteActions());

function updateOpenFileActions() {
  const file = activeFile.value;
  globalStore.setNoteActions([
    {
      key: "external-edit",
      label: editMode.value ? "Done" : "Edit",
      iconPath: editMode.value ? mdiCheck : mdiPencilOutline,
      visible: Boolean(file),
      iconOnly: true,
      handler: editMode.value ? finishEditing : () => setEditMode(true),
    },
    {
      key: "external-save",
      label: "Save",
      iconPath: mdiContentSaveOutline,
      visible: Boolean(file?.handle && file?.dirty),
      disabled: !canSaveActiveFile.value,
      unsaved: Boolean(file?.dirty),
      iconOnly: true,
      handler: () => {
        if (canSaveActiveFile.value) {
          saveActiveFile(false);
        }
      },
    },
    {
      key: "external-copy",
      label: copied.value ? "Copied" : "Copy",
      iconPath: copied.value ? mdiCheck : mdiContentCopy,
      visible: Boolean(file),
      iconOnly: true,
      handler: copyActiveFile,
    },
    {
      key: "external-choose",
      label: "Open",
      iconPath: mdiFolderOpenOutline,
      iconOnly: true,
      handler: chooseFile,
    },
    {
      key: "external-close",
      label: "Close",
      iconPath: mdiClose,
      visible: Boolean(file),
      iconOnly: true,
      handler: closeExternalFile,
    },
  ]);
  globalStore.setNoteMenuItems([]);
  globalStore.setNoteLayout({ kind: "markdown" });
}

async function chooseFile() {
  if (!confirmDiscardUnsavedChanges()) {
    return;
  }

  if (supportsNativeFileBridge()) {
    window.dispatchEvent(new CustomEvent("nirvnotes:open-native-file-dialog"));
    return;
  }

  if (window.showOpenFilePicker) {
    try {
      const handles = await window.showOpenFilePicker({
        multiple: true,
        types: [
          {
            description: "Text and Markdown files",
            accept: {
              "text/markdown": [".md"],
              "text/plain": [".txt", ".cfg", ".ini"],
            },
          },
        ],
      });
      const selectedFiles = [];
      for (const handle of handles) {
        selectedFiles.push({
          file: await handle.getFile(),
          handle,
        });
      }
      await loadFiles(selectedFiles, "Loaded from local file picker.");
    } catch (error) {
      if (error?.name !== "AbortError") {
        showStatus("Could not open the local file.", "error");
        console.error(error);
      }
    }
    return;
  }

  fileInput.value?.click();
}

function closeExternalFile() {
  if (!confirmDiscardUnsavedChanges()) {
    return;
  }

  files.value.forEach((file) => {
    documentSession.clearDraft(file.draftStorageKey);
  });
  files.value = [];
  activeKey.value = null;
  statusMessage.value = "";
  documentSession.leaveEdit();
  documentSession.setDirty(false);
  router.push({ name: "home" });
}

function activateFile(key) {
  if (key === activeKey.value) {
    return;
  }
  documentSession.leaveEdit();
  activeKey.value = key;
  restoreActiveDraft();
  documentSession.setDirty(Boolean(activeFile.value?.dirty));
}

async function fileInputChanged(event) {
  if (!confirmDiscardUnsavedChanges()) {
    event.target.value = "";
    return;
  }

  await loadFiles([...event.target.files], "Loaded from local file picker.");
  event.target.value = "";
}

async function loadFiles(selectedFiles, message) {
  const readableFiles = [];
  for (const selectedFile of selectedFiles) {
    readableFiles.push(await fileToPreview(selectedFile));
  }

  files.value = readableFiles;
  activeKey.value = readableFiles[0]?.key || null;
  documentSession.leaveEdit();
  documentSession.setDirty(false);
  if (readableFiles.length) {
    restoreActiveDraft();
    showStatus(message);
  }
}

async function fileToPreview(selectedFile) {
  const { file, handle } = normalizeSelectedFile(selectedFile);
  const content = await file.text();
  const extension = getExtension(file.name);
  const previewMarkdown = contentToPreviewMarkdown(
    content,
    extension,
    file.type,
  );
  const previewMode = isMarkdownFile(extension, file.type)
    ? "markdown"
    : "plain";

  return {
    key: `${file.name}-${file.size}-${file.lastModified}-${Math.random()
      .toString(36)
      .slice(2)}`,
    name: file.name,
    size: file.size,
    type: file.type,
    extension,
    handle,
    draftStorageKey: localDraftStorageKey(file, handle),
    content,
    draftContent: content,
    previewMode,
    previewMarkdown,
    lastModified: file.lastModified,
    dirty: false,
    draftRestored: false,
  };
}

function localDraftStorageKey(file, handle) {
  const identity = handle?.id || `${file.name}:${file.lastModified}`;
  return `local:${identity}`;
}

function restoreActiveDraft() {
  const file = activeFile.value;
  if (!file || file.draftRestored) {
    return;
  }

  file.draftRestored = true;
  const draft = documentSession.loadDraft(file.draftStorageKey);
  if (draft == null || draft === file.content) {
    return;
  }

  file.draftContent = draft;
  file.dirty = true;
  refreshPreview(file);
  documentSession.setDirty(true);
  showStatus("Unsaved local draft restored.");
}

function normalizeSelectedFile(selectedFile) {
  if (selectedFile?.file) {
    return {
      file: selectedFile.file,
      handle: selectedFile.handle || null,
    };
  }

  return {
    file: selectedFile,
    handle: null,
  };
}

function contentToPreviewMarkdown(content, extension, type) {
  return isMarkdownFile(extension, type)
    ? compactLeadingMarkdownMetadata(content)
    : fencedCode(content, codeLanguageForExtension(extension));
}

function isMarkdownFile(extension, type) {
  return extension === "md" || type === "text/markdown";
}

function getExtension(filename = "") {
  const match = filename.toLowerCase().match(/\.([^.]+)$/);
  return match ? match[1] : "";
}

function escapeHtml(value = "") {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function stripInlineMarkdown(value = "") {
  return String(value)
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .trim();
}

function normalizeMetadataKey(key = "") {
  return stripInlineMarkdown(key)
    .replace(/[*_`]+/g, "")
    .replace(/^[-*\s]+/, "")
    .replace(/\s*\/\s*/g, "/")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

function compactMetadataValue(key, value) {
  const normalizedKey = normalizeMetadataKey(key);
  const cleaned = stripInlineMarkdown(value);
  if (
    !cleaned ||
    normalizedKey === "original writer" ||
    normalizedKey === "writer"
  ) {
    return "";
  }

  if (normalizedKey === "domain") {
    return cleaned;
  }

  if (normalizedKey === "topic/subdomain") {
    return cleaned;
  }

  if (normalizedKey === "difficulty level") {
    return `difficulty ${cleaned}`;
  }

  if (normalizedKey === "tool use") {
    return `tools ${cleaned}`;
  }

  return "";
}

function compactLeadingMarkdownMetadata(markdown = "") {
  const normalized = String(markdown).replace(/\r\n?/g, "\n");
  const lines = normalized.split("\n");
  const firstHeadingIndex = lines.findIndex((line) => /^#{1,6}\s+/.test(line));
  if (firstHeadingIndex <= 0) {
    return markdown;
  }

  const leadingLines = lines.slice(0, firstHeadingIndex);
  const fieldPattern = /^\s*(?:[-*]\s+)?([^:\n]{2,48}):\s*(.+?)\s*$/;
  const fields = [];

  for (const line of leadingLines) {
    if (!line.trim()) {
      continue;
    }

    const match = line.match(fieldPattern);
    if (!match) {
      return markdown;
    }

    fields.push({ key: match[1], value: match[2] });
  }

  if (!fields.length) {
    return markdown;
  }

  const metaValues = fields
    .map((field) => compactMetadataValue(field.key, field.value))
    .filter(Boolean);
  const rest = lines.slice(firstHeadingIndex).join("\n").trimStart();
  if (!metaValues.length) {
    return rest;
  }

  const metaLine = metaValues.map(escapeHtml).join(" | ");
  return `<p class="flatnotes-external-meta-line"><strong>Meta</strong> ${metaLine}</p>\n\n${rest}`;
}

function fencedCode(content = "", language = "") {
  const fence = "```";
  const safeContent = String(content).replace(/```/g, "`` `");
  return `${fence}${language}\n${safeContent}\n${fence}\n`;
}

function noteTitleForFile(file) {
  const stem = file.name.replace(/\.[^.]+$/, "").trim() || "External file";
  return sanitizeTitle(stem);
}

function sanitizeTitle(value = "") {
  const title = value
    .replace(/[<>:"/\\|?*]/g, "-")
    .replace(/\s+/g, " ")
    .trim();
  return title || "External file";
}

function codeLanguageForExtension(extension = "") {
  if (extension === "ini") {
    return "ini";
  }

  if (extension === "json") {
    return "json";
  }

  return "";
}

function markActiveFileDirty() {
  if (!activeFile.value) {
    return;
  }

  activeFile.value.dirty =
    activeFile.value.draftContent !== activeFile.value.content;
  documentSession.setDirty(activeFile.value.dirty);
  if (activeFile.value.dirty) {
    documentSession.saveDraft(activeFile.value.draftContent);
  } else {
    documentSession.clearDraft();
  }
}

function refreshPreview(file) {
  file.previewMarkdown = contentToPreviewMarkdown(
    file.draftContent,
    file.extension,
    file.type,
  );
}

function setEditMode(value) {
  if (value) {
    documentSession.enterEdit();
  } else {
    documentSession.leaveEdit();
  }
}

function finishEditing() {
  if (!activeFile.value) {
    return;
  }
  if (activeFile.value.dirty) {
    saveActiveFile(true);
  } else {
    documentSession.leaveEdit();
  }
}

function saveActiveFile(close = false) {
  return documentSession.save({ close });
}

async function persistActiveFile() {
  const file = activeFile.value;
  if (!file) {
    return false;
  }

  if (!file.handle) {
    const error = new Error("Read-only: no writable file handle.");
    error.code = "read-only";
    throw error;
  }

  const savedFile = await localFileStorageAdapter.save({
    handle: file.handle,
    content: file.draftContent,
  });
  file.content = file.draftContent;
  file.size = savedFile.size;
  file.lastModified = savedFile.lastModified;
  file.dirty = false;
  refreshPreview(file);
  return savedFile;
}

function handleActiveFileSaveError(error) {
  if (error?.code === "permission-denied") {
    showStatus("Save permission denied.", "error");
  } else if (error?.code === "read-only") {
    showStatus(error.message, "error");
  } else {
    showStatus("Could not save to the original file.", "error");
  }
  console.error(error);
}

function confirmDiscardUnsavedChanges() {
  if (!files.value.some((file) => file.dirty)) {
    return true;
  }

  return window.confirm("Discard unsaved external file changes?");
}

async function consumeExternalLaunch(launch) {
  if (!launch || lastConsumedLaunchId.value === launch.id) {
    return;
  }

  lastConsumedLaunchId.value = launch.id;
  if (launch.files?.length) {
    if (!confirmDiscardUnsavedChanges()) {
      return;
    }

    await loadFiles(launch.files, launch.message || "Opened from Windows.");
    return;
  }

  showStatus(
    launch.message || "Could not open the file.",
    launch.tone || "error",
  );
}

function getActiveFileCopyPayload() {
  if (!activeFile.value) {
    return null;
  }

  const file = activeFile.value;
  const isMarkdown = file.extension === "md" || file.type === "text/markdown";
  const content = file.draftContent ?? file.content;
  return { type: isMarkdown ? "markdown" : "text", content };
}

function copyActiveFile() {
  return documentSession.copy("source");
}

function documentKeydownHandler(event) {
  documentSession.keydownHandler(event);
}

function formatBytes(bytes = 0) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function showStatus(message, tone = "info") {
  statusMessage.value = message;
  statusTone.value = tone;
}
</script>

<style scoped>
.flatnotes-open-file {
  width: min(100%, 68rem);
  margin-inline: auto;
}

.flatnotes-open-file-heading {
  min-width: 0;
  max-width: 100%;
  margin-bottom: 0.68rem;
}

.flatnotes-open-file-kicker-line {
  display: flex;
  min-width: 0;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.32rem;
  margin-bottom: 0.22rem;
}

.flatnotes-open-file-kicker {
  color: rgb(var(--theme-text-very-muted));
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0;
  line-height: 1;
  text-transform: uppercase;
}

.flatnotes-open-file-title {
  display: block;
  width: 100%;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: rgb(var(--theme-text));
  font-size: clamp(1.18rem, 4.2vw, 1.5rem);
  line-height: 1.15;
}

.flatnotes-open-file-strip {
  display: flex;
  min-height: 1.42rem;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.28rem;
  margin-bottom: 0.58rem;
  color: rgb(var(--theme-text-muted));
  font-size: 0.76rem;
  line-height: 1.1;
}

.flatnotes-open-file-status,
.flatnotes-open-file-meta {
  display: inline-flex;
  min-height: 1.18rem;
  align-items: center;
  gap: 0.22rem;
  border-radius: 999px;
  padding: 0 0.38rem;
  line-height: 1;
}

.flatnotes-open-file-status {
  color: rgb(var(--theme-text));
}

.flatnotes-open-file-status-error {
  color: rgb(var(--theme-danger));
}

.flatnotes-open-file-meta {
  border: 1px solid rgb(var(--theme-border));
  background-color: rgb(var(--theme-background-elevated) / 0.45);
  font-size: 0.72rem;
}

.flatnotes-open-file-meta span {
  color: rgb(var(--theme-text-very-muted));
  font-size: 0.62rem;
  font-weight: 700;
  text-transform: uppercase;
}

.flatnotes-open-file-meta strong {
  color: rgb(var(--theme-text));
  font-weight: 600;
}

.flatnotes-open-file-editor {
  display: block;
  width: 100%;
  min-height: min(68vh, 44rem);
  resize: vertical;
  border: 1px solid rgb(var(--theme-border));
  border-radius: 6px;
  padding: 1rem;
  color: rgb(var(--theme-text));
  background-color: rgb(var(--theme-background) / 0.82);
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono",
    "Courier New", monospace;
  font-size: 0.92rem;
  line-height: 1.55;
  outline: none;
}

.flatnotes-open-file-editor:focus {
  border-color: rgb(var(--theme-text-muted));
  background-color: rgb(var(--theme-background));
}

.flatnotes-open-file-plain-preview {
  margin: 0;
  min-height: min(58vh, 38rem);
  overflow-x: auto;
  white-space: pre-wrap;
  border-top: 1px solid rgb(var(--theme-border));
  border-bottom: 1px solid rgb(var(--theme-border));
  padding: 0.7rem 0;
  color: rgb(var(--theme-text));
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono",
    "Courier New", monospace;
  font-size: 0.86rem;
  line-height: 1.5;
}

:deep(.flatnotes-external-meta-line) {
  max-width: 100%;
  margin: 0 0 0.7rem 0 !important;
  color: rgb(var(--theme-text-muted));
  font-size: 0.8rem;
  line-height: 1.25;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:deep(.flatnotes-external-meta-line strong) {
  color: rgb(var(--theme-text-very-muted));
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

.flatnotes-open-file
  :deep(.toastui-editor-contents:not(.flatnotes-html-contents) h1) {
  font-size: 1.42rem;
}

.flatnotes-open-file
  :deep(.toastui-editor-contents:not(.flatnotes-html-contents) h2) {
  font-size: 1.22rem;
}

.flatnotes-open-file
  :deep(.toastui-editor-contents:not(.flatnotes-html-contents) h3) {
  font-size: 1.08rem;
}
</style>
