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
        <CustomButton
          label="Choose"
          :iconPath="mdiFolderOpenOutline"
          @click="chooseFile"
        />
        <CustomButton
          v-if="activeFile && canModify"
          label="Import"
          style="cta"
          :iconPath="mdiImport"
          @click="importActiveFile"
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
      </p>
    </div>
  </section>
</template>

<script setup>
import {
  mdiAlertCircleOutline,
  mdiCheckCircleOutline,
  mdiFileDocumentOutline,
  mdiFolderOpenOutline,
  mdiImport,
} from "@mdi/js";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { apiErrorHandler, createNote } from "../api.js";
import CustomButton from "../components/CustomButton.vue";
import IconLabel from "../components/IconLabel.vue";
import ToastViewer from "../components/toastui/ToastViewer.vue";
import { renderMarkdownToHtml } from "../components/work/workNote.js";
import { authTypes } from "../constants.js";
import { useGlobalStore } from "../globalStore.js";
import { getToastOptions } from "../helpers.js";

const canModify = computed(
  () => globalStore.config.authType != authTypes.readOnly,
);
const fileInput = ref();
const files = ref([]);
const activeKey = ref(null);
const globalStore = useGlobalStore();
const importInProgress = ref(false);
const router = useRouter();
const statusMessage = ref("");
const statusTone = ref("info");
const toast = useToast();

const activeFile = computed(
  () => files.value.find((file) => file.key === activeKey.value) || null,
);
const statusIcon = computed(() =>
  statusTone.value === "error" ? mdiAlertCircleOutline : mdiCheckCircleOutline,
);

onMounted(() => {
  if (supportsFileHandling()) {
    window.launchQueue.setConsumer(async (launchParams) => {
      const handles = launchParams.files || [];
      if (!handles.length) {
        return;
      }

      try {
        const launchedFiles = [];
        for (const handle of handles) {
          launchedFiles.push(await handle.getFile());
        }
        await loadFiles(launchedFiles, "Opened from Windows.");
      } catch (error) {
        showStatus("Could not read the file from Windows.", "error");
        console.error(error);
      }
    });
  } else {
    showStatus(
      "This browser can preview files here, but Windows file handling needs an installed Chromium PWA.",
    );
  }
});

function supportsFileHandling() {
  return (
    "launchQueue" in window &&
    "LaunchParams" in window &&
    "files" in window.LaunchParams.prototype
  );
}

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
  if (readableFiles.length) {
    showStatus(message);
  }
}

async function fileToPreview(file) {
  const content = await file.text();
  const extension = getExtension(file.name);
  const isConfig = extension === "cfg" || extension === "ini";
  const previewMarkdown = isConfig
    ? fencedCode(content, extension === "ini" ? "ini" : "")
    : content;

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
    previewMode: isConfig ? "code block" : "markdown",
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

async function importActiveFile() {
  if (!activeFile.value || importInProgress.value) {
    return;
  }

  importInProgress.value = true;
  try {
    const title = noteTitleForFile(activeFile.value);
    const note = await createNoteWithFallbackTitle(activeFile.value, title);
    toast.add(getToastOptions("File imported as note ✓", "Success", "success"));
    router.push({ name: "note", params: { title: note.title } });
  } catch (error) {
    apiErrorHandler(error, toast);
  } finally {
    importInProgress.value = false;
  }
}

async function createNoteWithFallbackTitle(file, title) {
  try {
    return await createNote(title, buildImportedFileHtml(file, title), "html");
  } catch (error) {
    if (error.response?.status !== 409) {
      throw error;
    }

    const fallbackTitle = `${title} imported ${timestampSuffix()}`;
    return createNote(fallbackTitle, buildImportedFileHtml(file, fallbackTitle), "html");
  }
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

function timestampSuffix() {
  return new Date()
    .toISOString()
    .replace(/[-:]/g, "")
    .replace(/\..+$/, "")
    .replace("T", "-");
}

function buildImportedFileHtml(file, title) {
  const rendered = renderMarkdownToHtml(file.previewMarkdown);
  const sourceFilename = escapeHtml(file.name);
  const escapedTitle = escapeHtml(title);

  return `<!doctype html>
<html lang="de">
  <head>
    <meta charset="utf-8">
    <meta name="flatnotes-note-kind" content="research">
    <title>${escapedTitle}</title>
  </head>
  <body>
    <article class="flatnote flatnote-imported-file" data-flatnotes-note-kind="research">
      <p class="flatnote-kicker">Imported File</p>
      <h1>${escapedTitle}</h1>
      <section class="flatnote-summary" data-flatnotes-component="summary">
        <p>Imported from <code>${sourceFilename}</code>. Original text is preserved in the note source.</p>
      </section>
      <section class="flatnote-imported-file-body" data-flatnotes-component="external-file-body">
${rendered}
      </section>
      <template data-flatnotes-external-source data-filename="${escapeAttribute(file.name)}">${escapeHtml(file.content)}</template>
    </article>
  </body>
</html>`;
}

function escapeHtml(value = "") {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function escapeAttribute(value = "") {
  return escapeHtml(value).replace(/'/g, "&#39;");
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
</style>
