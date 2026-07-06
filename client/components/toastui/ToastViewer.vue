<template>
  <div ref="viewerElement"></div>
</template>

<script setup>
import Viewer from "@toast-ui/editor/dist/toastui-editor-viewer";
import { onMounted, ref, watch } from "vue";

import baseOptions from "./baseOptions.js";
import extendedAutolinks from "./extendedAutolinks.js";

const props = defineProps({
  initialValue: String,
  enhanceNoteLead: {
    type: Boolean,
    default: true,
  },
  noteTitle: String,
  taskCheckboxToggleHandler: Function,
  taskCheckboxesDisabled: Boolean,
});

const viewerElement = ref();
let renderEnhancementsPromise = null;

function loadRenderEnhancements() {
  if (!renderEnhancementsPromise) {
    renderEnhancementsPromise = import("./renderEnhancements.js");
  }

  return renderEnhancementsPromise;
}

onMounted(async () => {
  new Viewer({
    ...baseOptions,
    extendedAutolinks,
    el: viewerElement.value,
    initialValue: props.initialValue,
  });
  const { enhanceRenderedMarkdown } = await loadRenderEnhancements();
  await enhanceRenderedMarkdown(viewerElement.value, {
    noteLead: props.enhanceNoteLead,
    noteTitle: props.noteTitle,
    taskList: getTaskListOptions(),
  });
});

function getTaskListOptions() {
  return {
    disabled: props.taskCheckboxesDisabled,
    onToggle: props.taskCheckboxToggleHandler,
  };
}

watch(
  () => props.taskCheckboxesDisabled,
  async () => {
    const { enhanceTaskListCheckboxes } = await loadRenderEnhancements();
    enhanceTaskListCheckboxes(viewerElement.value, getTaskListOptions());
  },
);
</script>

<style>
@import "@toast-ui/editor/dist/toastui-editor-viewer.css";
@import "katex/dist/katex.min.css";
@import "prismjs/themes/prism.css";
@import "@toast-ui/editor-plugin-code-syntax-highlight/dist/toastui-editor-plugin-code-syntax-highlight.css";
@import "./toastui-editor-overrides.scss";
</style>
