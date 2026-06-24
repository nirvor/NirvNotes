<template>
  <div ref="viewerElement" class="flatnotes-html-viewer">
    <div
      class="toastui-editor-contents flatnotes-html-contents"
      v-html="html"
    ></div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue";

import { enhanceRenderedMarkdown } from "../toastui/renderEnhancements.js";

const props = defineProps({
  initialValue: String,
  noteTitle: String,
  taskCheckboxToggleHandler: Function,
  taskCheckboxesDisabled: Boolean,
});

const viewerElement = ref();

const html = computed(() =>
  sanitizeHtml(extractRenderableHtml(props.initialValue || "")),
);

function isFullHtmlDocument(value) {
  return /<(?:!doctype|html|head|body)\b/i.test(value);
}

function extractRenderableHtml(value) {
  if (!isFullHtmlDocument(value)) {
    return value;
  }

  const documentValue = new DOMParser().parseFromString(value, "text/html");
  return documentValue.body?.innerHTML || value;
}

function sanitizeHtml(value) {
  const documentValue = new DOMParser().parseFromString(value, "text/html");

  documentValue
    .querySelectorAll("script, iframe[src^='javascript:']")
    .forEach((element) => element.remove());

  documentValue.querySelectorAll("*").forEach((element) => {
    [...element.attributes].forEach((attribute) => {
      const name = attribute.name.toLowerCase();
      const rawValue = attribute.value.trim().toLowerCase();

      if (name.startsWith("on")) {
        element.removeAttribute(attribute.name);
      }

      if (
        (name === "href" || name === "src") &&
        rawValue.startsWith("javascript:")
      ) {
        element.removeAttribute(attribute.name);
      }
    });
  });

  return documentValue.body.innerHTML;
}

function getTaskListOptions() {
  return {
    disabled: props.taskCheckboxesDisabled,
    onToggle: props.taskCheckboxToggleHandler,
  };
}

async function enhance() {
  await nextTick();
  await enhanceRenderedMarkdown(viewerElement.value, {
    noteTitle: props.noteTitle,
    taskList: getTaskListOptions(),
  });
}

watch(() => props.initialValue, enhance);
watch(() => props.taskCheckboxesDisabled, enhance);
onMounted(enhance);
</script>

<style>
@import "@toast-ui/editor/dist/toastui-editor-viewer.css";
@import "katex/dist/katex.min.css";
@import "prismjs/themes/prism.css";
@import "@toast-ui/editor-plugin-code-syntax-highlight/dist/toastui-editor-plugin-code-syntax-highlight.css";
@import "../toastui/toastui-editor-overrides.scss";
</style>
