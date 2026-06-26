<template>
  <section class="flatnotes-work-viewer">
    <div class="flatnotes-work-viewer-toolbar print:hidden">
      <button
        type="button"
        class="flatnotes-work-viewer-copy"
        :class="{ 'flatnotes-work-viewer-copy-active': copied }"
        :title="copied ? 'Copied' : 'Copy markdown'"
        :aria-label="copied ? 'Copied' : 'Copy markdown'"
        @click="copyMarkdown"
      >
        <SvgIcon
          type="mdi"
          :path="copied ? mdiCheck : mdiContentCopy"
          size="0.78rem"
        />
      </button>
    </div>
    <ToastViewer
      :key="markdown"
      :initialValue="markdown"
      :enhance-note-lead="false"
      :note-title="noteTitle"
      :task-checkboxes-disabled="taskCheckboxesDisabled"
      :task-checkbox-toggle-handler="taskCheckboxToggleHandler"
      class="toast-viewer min-w-0 max-w-full pb-4"
    />
  </section>
</template>

<script setup>
import SvgIcon from "@jamescoyle/vue-icon";
import { mdiCheck, mdiContentCopy } from "@mdi/js";
import { computed, ref } from "vue";

import { writeMarkdownToClipboard } from "../../clipboard.js";
import ToastViewer from "../toastui/ToastViewer.vue";
import { extractWorkMarkdown } from "./workNote.js";

const props = defineProps({
  initialValue: String,
  noteTitle: String,
  taskCheckboxToggleHandler: Function,
  taskCheckboxesDisabled: Boolean,
});

const copied = ref(false);
const markdown = computed(() => extractWorkMarkdown(props.initialValue || ""));

async function copyMarkdown() {
  try {
    await writeMarkdownToClipboard(markdown.value);
    copied.value = true;
    setTimeout(() => {
      copied.value = false;
    }, 1400);
  } catch {
    copied.value = false;
  }
}
</script>

<style lang="scss" scoped>
.flatnotes-work-viewer {
  position: relative;
  min-width: 0;
  max-width: 100%;
}

.flatnotes-work-viewer-toolbar {
  position: absolute;
  top: 0;
  right: 0;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  margin: 0;
}

.flatnotes-work-viewer :deep(.toastui-editor-contents > :first-child) {
  padding-right: 2rem;
}

.flatnotes-work-viewer-copy {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.42rem;
  height: 1.42rem;
  border: 1px solid rgb(var(--theme-border));
  border-radius: 6px;
  padding: 0;
  color: rgb(var(--theme-text-muted));
  background-color: transparent;
  touch-action: manipulation;
}

.flatnotes-work-viewer-copy:hover,
.flatnotes-work-viewer-copy:focus-visible,
.flatnotes-work-viewer-copy-active {
  border-color: rgb(var(--theme-brand));
  color: rgb(var(--theme-brand));
}
</style>
