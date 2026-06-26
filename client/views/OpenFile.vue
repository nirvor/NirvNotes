<template>
  <section class="flatnotes-open-file min-w-0 max-w-full">
    <div class="mb-3 flex min-w-0 flex-col gap-2 md:flex-row md:items-end md:justify-between">
      <div class="min-w-0">
        <p class="mb-1 text-[0.68rem] font-bold uppercase text-theme-text-very-muted">
          External File
        </p>
        <h1 class="truncate text-2xl leading-tight md:text-3xl">
          {{ activeFile ? activeFile.name : "Open a local file" }}
        </h1>
      </div>

      <div class="flex shrink-0 gap-2 print:hidden">
        <button
          v-if="activeFile"
          type="button"
          class="flatnotes-open-file-icon-button"
          :title="copied ? 'Copied raw source' : 'Copy raw source'"
          :aria-label="copied ? 'Copied raw source' : 'Copy raw source'"
          @click="copyActiveFile"
        >
          <SvgIcon
            type="mdi"
            :path="copied ? mdiCheck : mdiContentCopy"
            size="1rem"
          />
        </button>
        <button
          type="button"
          class="flatnotes-open-file-icon-button"
          title="Choose another local file"
          aria-label="Choose another local file"
          @click="chooseFile"
        >
          <SvgIcon type="mdi" :path="mdiFolderOpenOutline" size="1rem" />
        </button>
        <button
          type="button"
          class="flatnotes-open-file-icon-button"
          title="Close external file"
          aria-label="Close external file"
          @click="closeExternalFile"
        >
          <SvgIcon type="mdi" :path="mdiClose" size="1rem" />
        </button>
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

    <div v-if="statusMessage || activeFile" class="flatnotes-open-file-strip">
      <span
        v-if="statusMessage"
        class="flatnotes-open-file-status"
        :class="{ 'flatnotes-open-file-status-error': statusTone === 'error' }"
      >
        <SvgIcon type="mdi" :path="statusIcon" size="0.76rem" />
        {{ statusMessage }}
      </span>
      <span
        v-for="item in metadataItems"
        :key="item.label"
        class="flatnotes-open-file-meta"
      >
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
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

    <ToastViewer
      v-if="activeFile"
      :key="activeFile.key"
      :initialValue="activeFile.previewMarkdown"
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
  mdiContentCopy,
  mdiFileDocumentOutline,
  mdiFolderOpenOutline,
} from "@mdi/js";
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import {
  writeMarkdownToClipboard,
  writePlainTextToClipboard,
} from "../clipboard.js";
import IconLabel from "../components/IconLabel.vue";
import ToastViewer from "../components/toastui/ToastViewer.vue";
import {
  externalFileLaunch,
  supportsFileHandlingLaunchQueue,
} from "../externalFiles.js";

const copied = ref(false);
const fileInput = ref();
const files = ref([]);
const activeKey = ref(null);
const lastConsumedLaunchId = ref(null);
const statusMessage = ref("");
const statusTone = ref("info");
const router = useRouter();

const activeFile = computed(
  () => files.value.find((file) => file.key === activeKey.value) || null,
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
const statusIcon = computed(() =>
  statusTone.value === "error" ? mdiAlertCircleOutline : mdiCheckCircleOutline,
);

onMounted(() => {
  if (!supportsFileHandlingLaunchQueue()) {
    showStatus(
      "This browser can preview files here, but Windows file opening needs the installed NirvNotes app.",
    );
  }
});

watch(externalFileLaunch, consumeExternalLaunch, { immediate: true });

function chooseFile() {
  fileInput.value?.click();
}

function closeExternalFile() {
  files.value = [];
  activeKey.value = null;
  statusMessage.value = "";
  copied.value = false;
  router.push({ name: "home" });
}

async function fileInputChanged(event) {
  await loadFiles([...event.target.files], "Loaded from local file picker.");
  event.target.value = "";
}

async function loadFiles(selectedFiles, message) {
  const readableFiles = [];
  for (const file of selectedFiles) {
    readableFiles.push(await fileToPreview(file));
  }

  files.value = readableFiles;
  activeKey.value = readableFiles[0]?.key || null;
  copied.value = false;
  if (readableFiles.length) {
    showStatus(message);
  }
}

async function fileToPreview(file) {
  const content = await file.text();
  const extension = getExtension(file.name);
  const isMarkdown = extension === "md" || file.type === "text/markdown";
  const previewMarkdown = isMarkdown
    ? compactLeadingMarkdownMetadata(content)
    : fencedCode(content, codeLanguageForExtension(extension));

  return {
    key: `${file.name}-${file.size}-${file.lastModified}-${Math.random()
      .toString(36)
      .slice(2)}`,
    name: file.name,
    size: file.size,
    type: file.type,
    extension,
    content,
    previewMarkdown,
    lastModified: file.lastModified,
  };
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
  return key.toLowerCase().replace(/\s+/g, " ").trim();
}

function compactMetadataValue(key, value) {
  const normalizedKey = normalizeMetadataKey(key);
  const cleaned = stripInlineMarkdown(value);
  if (!cleaned || normalizedKey === "original writer") {
    return "";
  }

  if (normalizedKey === "domain") {
    return cleaned;
  }

  if (normalizedKey === "topic / subdomain" || normalizedKey === "topic/subdomain") {
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

async function consumeExternalLaunch(launch) {
  if (!launch || lastConsumedLaunchId.value === launch.id) {
    return;
  }

  lastConsumedLaunchId.value = launch.id;
  if (launch.files?.length) {
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
  if (isMarkdown) {
    await writeMarkdownToClipboard(file.content);
  } else {
    await writePlainTextToClipboard(file.content);
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

.flatnotes-open-file-icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  min-height: 1.75rem;
  border: 1px solid rgb(var(--theme-border));
  border-radius: 6px;
  color: rgb(var(--theme-text));
  background-color: rgb(var(--theme-background));
  touch-action: manipulation;
}

.flatnotes-open-file-icon-button:hover,
.flatnotes-open-file-icon-button:focus-visible {
  border-color: rgb(var(--theme-brand));
  color: rgb(var(--theme-brand));
  background-color: rgb(var(--theme-background-elevated));
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

@media (max-width: 640px) and (pointer: coarse), (max-width: 640px) and (hover: none) {
  .flatnotes-open-file-icon-button {
    width: 2rem;
    min-height: 2rem;
  }
}
</style>
