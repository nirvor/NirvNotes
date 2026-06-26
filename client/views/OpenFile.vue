<template>
  <section class="flatnotes-open-file min-w-0 max-w-full">
    <div class="mb-5 flex min-w-0 flex-col gap-3 md:flex-row md:items-end md:justify-between">
      <div class="min-w-0">
        <p class="mb-1 text-xs font-bold uppercase text-theme-text-very-muted">
          External File
        </p>
        <h1 class="truncate text-3xl leading-tight">
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
        <CustomButton
          label="Choose"
          :iconPath="mdiFolderOpenOutline"
          @click="chooseFile"
        />
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

    <div
      v-if="statusMessage"
      class="mb-4 rounded-md border border-theme-border bg-theme-background-elevated px-3 py-2 text-theme-text-muted"
    >
      <IconLabel
        :iconPath="statusIcon"
        class="mr-2 inline-flex"
      />
      <span>{{ statusMessage }}</span>
    </div>

    <div
      v-if="files.length > 1"
      class="mb-4 flex flex-wrap gap-2 print:hidden"
    >
      <button
        v-for="file in files"
        :key="file.key"
        type="button"
        class="rounded-full border border-theme-border px-3 py-1 text-sm hover:border-theme-brand hover:text-theme-brand"
        :class="{
          'border-theme-brand text-theme-brand': activeFile?.key === file.key,
        }"
        @click="activeKey = file.key"
      >
        {{ file.name }}
      </button>
    </div>

    <div
      v-if="activeFile"
      class="mb-4 grid gap-2 text-sm text-theme-text-muted md:grid-cols-3"
    >
      <div class="rounded-md border border-theme-border bg-theme-background-elevated px-3 py-2">
        <span class="block text-xs font-bold uppercase text-theme-text-very-muted">
          Type
        </span>
        {{ activeFile.extension || "text" }}
      </div>
      <div class="rounded-md border border-theme-border bg-theme-background-elevated px-3 py-2">
        <span class="block text-xs font-bold uppercase text-theme-text-very-muted">
          Size
        </span>
        {{ formatBytes(activeFile.size) }}
      </div>
      <div class="rounded-md border border-theme-border bg-theme-background-elevated px-3 py-2">
        <span class="block text-xs font-bold uppercase text-theme-text-very-muted">
          Preview
        </span>
        {{ activeFile.previewMode }}
      </div>
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
      class="rounded-md border border-dashed border-theme-border px-4 py-8 text-center text-theme-text-muted"
    >
      <IconLabel
        :iconPath="mdiFileDocumentOutline"
        iconSize="2rem"
        class="mb-3 justify-center"
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
  mdiContentCopy,
  mdiFileDocumentOutline,
  mdiFolderOpenOutline,
} from "@mdi/js";
import { computed, onMounted, ref, watch } from "vue";

import {
  writeMarkdownToClipboard,
  writePlainTextToClipboard,
} from "../clipboard.js";
import CustomButton from "../components/CustomButton.vue";
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

const activeFile = computed(
  () => files.value.find((file) => file.key === activeKey.value) || null,
);
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
    ? content
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
    previewMode: isMarkdown ? "markdown" : "plain text",
    lastModified: file.lastModified,
  };
}

function getExtension(filename = "") {
  const match = filename.toLowerCase().match(/\.([^.]+)$/);
  return match ? match[1] : "";
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

.flatnotes-open-file-icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  min-height: 2rem;
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
</style>
