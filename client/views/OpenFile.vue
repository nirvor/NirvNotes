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

    <div v-if="files.length > 1" class="mb-3 flex flex-wrap gap-1.5 print:hidden">
      <button
        v-for="file in files"
        :key="file.key"
        type="button"
        class="rounded-full border border-theme-border px-2 py-0.5 text-xs hover:border-theme-brand hover:text-theme-brand"
        :class="{
          'border-theme-brand text-theme-brand': activeFile?.key === file.key,
        }"
        @click="activeKey = file.key"
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
      @keydown.ctrl.s.prevent="saveActiveFile"
      @keydown.meta.s.prevent="saveActiveFile"
    ></textarea>

    <pre
      v-else-if="activeFile && activeFile.previewMode === 'plain'"
      class="flatnotes-open-file-plain-preview"
    >{{ activeFile.draftContent }}</pre>

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
        Open a .md, .txt, .cfg, or .ini file through Windows, or choose one here.
        Nothing is saved into NirvNotes.
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
  mdiEyeOutline,
  mdiFileDocumentOutline,
  mdiFolderOpenOutline,
  mdiPencilOutline,
} from "@mdi/js";
import {
  computed,
  defineAsyncComponent,
  nextTick,
  onMounted,
  onUnmounted,
  ref,
  watch,
  watchEffect,
} from "vue";
import { useRouter } from "vue-router";

import {
  writeMarkdownToClipboard,
  writePlainTextToClipboard,
} from "../clipboard.js";
import IconLabel from "../components/IconLabel.vue";
import {
  externalFileLaunch,
  supportsFileHandlingLaunchQueue,
  supportsNativeFileBridge,
} from "../externalFiles.js";
import { useGlobalStore } from "../globalStore.js";

const ToastViewer = defineAsyncComponent(() =>
  import("../components/toastui/ToastViewer.vue"),
);

const copied = ref(false);
const editMode = ref(false);
const editorTextarea = ref();
const fileInput = ref();
const files = ref([]);
const activeKey = ref(null);
const lastConsumedLaunchId = ref(null);
const statusMessage = ref("");
const statusTone = ref("info");
const router = useRouter();
const globalStore = useGlobalStore();
const editDoubleTapDelayMs = 420;
const editDoubleTapDistancePx = 28;
let lastContentTap = null;

const activeFile = computed(
  () => files.value.find((file) => file.key === activeKey.value) || null,
);
const canSaveActiveFile = computed(
  () =>
    Boolean(activeFile.value?.handle) &&
    Boolean(activeFile.value?.dirty) &&
    !activeFile.value?.saving,
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
const saveButtonTitle = computed(() => {
  if (!activeFile.value?.handle) {
    return "Read-only: no writable file handle";
  }

  return activeFile.value.dirty ? "Save to original file" : "Saved";
});

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
      label: editMode.value ? "Preview" : "Edit",
      iconPath: editMode.value ? mdiEyeOutline : mdiPencilOutline,
      visible: Boolean(file),
      iconOnly: true,
      handler: toggleEditMode,
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
          saveActiveFile();
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

  files.value = [];
  activeKey.value = null;
  statusMessage.value = "";
  copied.value = false;
  editMode.value = false;
  router.push({ name: "home" });
}

function isIgnoredEditTriggerTarget(target) {
  if (!(target instanceof Element)) {
    return false;
  }

  return Boolean(
    target.closest(
      [
        "a",
        "button",
        "input",
        "textarea",
        "select",
        "label",
        "summary",
        "[role='button']",
        "pre",
        "code",
        ".flatnotes-code-block-wrapper",
        ".flatnotes-bottom-tags",
        ".flatnotes-media-button",
        ".flatnotes-media-lightbox",
        ".katex",
      ].join(","),
    ),
  );
}

function canStartEditFromContent(event, { allowSelection = false } = {}) {
  const selection = window.getSelection?.();
  const hasSelection = Boolean(
    selection && !selection.isCollapsed && selection.toString(),
  );

  return (
    Boolean(activeFile.value) &&
    !editMode.value &&
    !event.defaultPrevented &&
    (event.button == null || event.button === 0) &&
    (allowSelection || !hasSelection) &&
    !isIgnoredEditTriggerTarget(event.target)
  );
}

function startEditFromContent(event, options = {}) {
  if (!canStartEditFromContent(event, options)) {
    return false;
  }

  event.preventDefault();
  setEditMode(true);
  return true;
}

function openFileDblClickHandler(event) {
  lastContentTap = null;
  startEditFromContent(event, { allowSelection: true });
}

function openFilePointerUpHandler(event) {
  const previousTap = lastContentTap;
  if (
    !canStartEditFromContent(event, {
      allowSelection: Boolean(previousTap),
    })
  ) {
    lastContentTap = null;
    return;
  }

  const now = window.performance?.now?.() || Date.now();
  const nextTap = {
    time: now,
    x: event.clientX,
    y: event.clientY,
  };

  lastContentTap = nextTap;
  window.setTimeout(() => {
    if (lastContentTap === nextTap) {
      lastContentTap = null;
    }
  }, editDoubleTapDelayMs + 40);

  if (!previousTap || now - previousTap.time > editDoubleTapDelayMs) {
    return;
  }

  const distance = Math.hypot(
    event.clientX - previousTap.x,
    event.clientY - previousTap.y,
  );
  if (distance > editDoubleTapDistancePx) {
    return;
  }

  lastContentTap = null;
  startEditFromContent(event, { allowSelection: true });
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
  copied.value = false;
  editMode.value = false;
  if (readableFiles.length) {
    showStatus(message);
  }
}

async function fileToPreview(selectedFile) {
  const { file, handle } = normalizeSelectedFile(selectedFile);
  const content = await file.text();
  const extension = getExtension(file.name);
  const previewMarkdown = contentToPreviewMarkdown(content, extension, file.type);
  const previewMode = isMarkdownFile(extension, file.type) ? "markdown" : "plain";

  return {
    key: `${file.name}-${file.size}-${file.lastModified}-${Math.random()
      .toString(36)
      .slice(2)}`,
    name: file.name,
    size: file.size,
    type: file.type,
    extension,
    handle,
    content,
    draftContent: content,
    previewMode,
    previewMarkdown,
    lastModified: file.lastModified,
    dirty: false,
    saving: false,
  };
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
  if (!cleaned || normalizedKey === "original writer" || normalizedKey === "writer") {
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

  activeFile.value.dirty = activeFile.value.draftContent !== activeFile.value.content;
}

function refreshPreview(file) {
  file.previewMarkdown = contentToPreviewMarkdown(
    file.draftContent,
    file.extension,
    file.type,
  );
}

function toggleEditMode() {
  if (!activeFile.value) {
    return;
  }

  if (editMode.value) {
    refreshPreview(activeFile.value);
  }
  setEditMode(!editMode.value);
}

function setEditMode(value) {
  editMode.value = value;
  if (editMode.value) {
    nextTick(() => editorTextarea.value?.focus({ preventScroll: true }));
  }
}

async function saveActiveFile() {
  const file = activeFile.value;
  if (!file) {
    return;
  }

  if (!file.handle) {
    showStatus("Read-only: no writable file handle.", "error");
    return;
  }

  try {
    file.saving = true;
    const hasPermission = await ensureWritePermission(file.handle);
    if (!hasPermission) {
      showStatus("Save permission denied.", "error");
      return;
    }

    const writable = await file.handle.createWritable();
    await writable.write(file.draftContent);
    await writable.close();

    const savedFile = await file.handle.getFile();
    file.content = file.draftContent;
    file.size = savedFile.size;
    file.lastModified = savedFile.lastModified;
    file.dirty = false;
    refreshPreview(file);
    showStatus("Saved to original file.");
  } catch (error) {
    showStatus("Could not save to the original file.", "error");
    console.error(error);
  } finally {
    file.saving = false;
  }
}

async function ensureWritePermission(handle) {
  const options = { mode: "readwrite" };
  if (handle.queryPermission) {
    const permission = await handle.queryPermission(options);
    if (permission === "granted") {
      return true;
    }
  }

  if (handle.requestPermission) {
    return (await handle.requestPermission(options)) === "granted";
  }

  return true;
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

  showStatus(launch.message || "Could not open the file.", launch.tone || "error");
}

async function copyActiveFile() {
  if (!activeFile.value) {
    return;
  }

  const file = activeFile.value;
  const isMarkdown = file.extension === "md" || file.type === "text/markdown";
  const content = file.draftContent ?? file.content;
  if (isMarkdown) {
    await writeMarkdownToClipboard(content);
  } else {
    await writePlainTextToClipboard(content);
  }

  copied.value = true;
  showStatus("Copied raw source to clipboard.");
  window.setTimeout(() => {
    copied.value = false;
  }, 1400);
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

.flatnotes-open-file :deep(.toastui-editor-contents:not(.flatnotes-html-contents) h1) {
  font-size: 1.42rem;
}

.flatnotes-open-file :deep(.toastui-editor-contents:not(.flatnotes-html-contents) h2) {
  font-size: 1.22rem;
}

.flatnotes-open-file :deep(.toastui-editor-contents:not(.flatnotes-html-contents) h3) {
  font-size: 1.08rem;
}
</style>
