<template>
  <div ref="viewerElement"></div>
</template>

<script setup>
import Viewer from "@toast-ui/editor/dist/toastui-editor-viewer";
import { onMounted, ref, watch } from "vue";

import baseOptions from "./baseOptions.js";
import extendedAutolinks from "./extendedAutolinks.js";
import {
  enhanceRenderedMarkdown,
  enhanceTaskListCheckboxes,
} from "./renderEnhancements.js";

const props = defineProps({
  initialValue: String,
  taskCheckboxToggleHandler: Function,
  taskCheckboxesDisabled: Boolean,
});

const viewerElement = ref();

onMounted(async () => {
  new Viewer({
    ...baseOptions,
    extendedAutolinks,
    el: viewerElement.value,
    initialValue: props.initialValue,
  });
  await enhanceRenderedMarkdown(viewerElement.value, {
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
  () => {
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
