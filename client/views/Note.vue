<template>
  <!-- Confirm Deletion Modal -->
  <ConfirmModal
    v-model="isDeleteModalVisible"
    title="Confirm Deletion"
    :message="`Are you sure you want to delete the note '${note.title}'?`"
    confirmButtonText="Delete"
    confirmButtonStyle="danger"
    @confirm="deleteConfirmedHandler"
  />

  <!-- Save Changes Modal -->
  <ConfirmModal
    v-model="isSaveChangesModalVisible"
    title="Save Changes"
    message="Do you want to save your changes?"
    confirmButtonText="Save"
    confirmButtonStyle="success"
    rejectButtonText="Discard"
    rejectButtonStyle="danger"
    @confirm="saveHandler((close = true))"
    @reject="closeNote"
  />

  <!-- Draft Modal -->
  <ConfirmModal
    v-model="isDraftModalVisible"
    title="Draft Detected"
    message="There is an unsaved draft of this note stored in this browser. Do you want to resume the draft version or delete it?"
    confirmButtonText="Resume Draft"
    confirmButtonStyle="cta"
    rejectButtonText="Delete Draft"
    rejectButtonStyle="danger"
    @confirm="setEditMode()"
    @reject="
      clearDraft();
      setEditMode();
    "
  />

  <LoadingIndicator
    ref="loadingIndicator"
    :class="[
      'flatnotes-note-shell flex h-full min-w-0 max-w-full flex-col',
      {
        'flatnotes-note-shell-wide': isWideDashboardNote,
        'flatnotes-note-shell-work': noteLayoutKind === 'work',
        'flatnotes-note-shell-research': noteLayoutKind === 'research',
        'flatnotes-note-shell-markdown': noteLayoutKind === 'markdown',
      },
    ]"
  >
    <!-- Header -->
    <div class="min-w-0 max-w-full">
      <!-- Title -->
      <div class="min-w-0 max-w-full grow truncate text-2xl leading-[1.35em]">
        <span v-show="!editMode" :title="note.title">{{ note.title }}</span>
        <input
          v-show="editMode"
          v-model.trim="newTitle"
          class="w-full bg-theme-background outline-none"
          placeholder="Title"
        />
      </div>
    </div>

    <hr v-if="!editMode" class="my-2 border-theme-border" />

    <!-- Content -->
    <div
      class="flatnotes-note-content min-w-0 max-w-full flex-1"
      @dblclick="noteContentDblClickHandler"
      @pointerup="noteContentPointerUpHandler"
    >
      <ToastViewer
        v-if="!editMode && !isHtmlFormat"
        :initialValue="note.content"
        :note-title="note.title"
        :task-checkboxes-disabled="!canModify"
        :task-checkbox-toggle-handler="toggleTaskCheckbox"
        class="toast-viewer min-w-0 max-w-full pb-4"
      />
      <WorkNoteViewer
        v-if="!editMode && isWorkNote"
        :initialValue="note.content"
        :note-title="note.title"
        :task-checkboxes-disabled="!canModify"
        :task-checkbox-toggle-handler="toggleTaskCheckbox"
      />
      <HtmlViewer
        v-if="!editMode && isHtmlFormat && !isWorkNote"
        :initialValue="note.content"
        :note-title="note.title"
        :task-checkboxes-disabled="!canModify"
        :task-checkbox-toggle-handler="toggleTaskCheckbox"
        class="toast-viewer min-w-0 max-w-full pb-4"
      />
      <ToastEditor
        v-if="editMode && editorFormat === 'markdown'"
        ref="contentEditor"
        :initialValue="getInitialEditorValue()"
        :initialEditType="loadDefaultEditorMode()"
        :addImageBlobHook="addImageBlobHook"
        @change="startContentChangedTimeout"
        @keydown="keydownHandler"
      />
      <WorkNoteEditor
        v-if="editMode && editorFormat === 'html' && editorKind === 'work'"
        :key="editorKey"
        ref="contentEditor"
        :current-kind="editorKind"
        :initialValue="getInitialEditorValue()"
        :note-title="newTitle"
        :addImageBlobHook="addImageBlobHook"
        :show-kind-switch="isNewNote"
        @change="startContentChangedTimeout"
        @keydown="keydownHandler"
        @set-kind="setNewNoteKind"
      />
      <HtmlEditor
        v-if="editMode && editorFormat === 'html' && editorKind === 'research'"
        :key="editorKey"
        ref="contentEditor"
        :current-kind="editorKind"
        :initialValue="getInitialEditorValue()"
        :addImageBlobHook="addImageBlobHook"
        :show-kind-switch="isNewNote"
        @change="startContentChangedTimeout"
        @keydown="keydownHandler"
        @set-kind="setNewNoteKind"
      />
    </div>
  </LoadingIndicator>
</template>

<script setup>
import {
  mdiCodeTags,
  mdiContentCopy,
  mdiLanguageHtml5,
  mdiLinkVariant,
  mdiNoteOffOutline,
  mdiTextBoxOutline,
} from "@mdi/js";
import { mdilContentSave, mdilDelete } from "@mdi/light-js";
import Mousetrap from "mousetrap";
import { useToast } from "primevue/usetoast";
import {
  computed,
  nextTick,
  onMounted,
  onUnmounted,
  ref,
  watch,
  watchEffect,
} from "vue";
import { useRouter } from "vue-router";

import {
  apiErrorHandler,
  createAttachment,
  createNote,
  deleteNote,
  getNote,
  updateNote,
} from "../api.js";
import { Note } from "../classes.js";
import {
  writeHtmlToClipboard,
  writeMarkdownToClipboard,
  writePlainTextToClipboard,
} from "../clipboard.js";
import ConfirmModal from "../components/ConfirmModal.vue";
import HtmlEditor from "../components/html/HtmlEditor.vue";
import HtmlViewer from "../components/html/HtmlViewer.vue";
import LoadingIndicator from "../components/LoadingIndicator.vue";
import ToastEditor from "../components/toastui/ToastEditor.vue";
import ToastViewer from "../components/toastui/ToastViewer.vue";
import WorkNoteEditor from "../components/work/WorkNoteEditor.vue";
import WorkNoteViewer from "../components/work/WorkNoteViewer.vue";
import {
  buildWorkNoteHtml,
  extractWorkMarkdown,
  isWorkNoteHtml,
} from "../components/work/workNote.js";
import { authTypes } from "../constants.js";
import { useGlobalStore } from "../globalStore.js";
import { getToastOptions } from "../helpers.js";
import { isCurrentTokenStored } from "../tokenStorage.js";

const props = defineProps({
  title: String,
  initialTitle: String,
});

const canModify = computed(
  () => globalStore.config.authType != authTypes.readOnly,
);
const isHtmlFormat = computed(() => (note.value.format || "html") === "html");
const isWorkNote = computed(
  () => isHtmlFormat.value && isWorkNoteHtml(note.value.content || ""),
);
const isWideDashboardNote = computed(
  () =>
    isHtmlFormat.value &&
    /class=["'][^"']*\b(?:nirv-dashboard-v[345]|nirv-board)\b/.test(
      note.value.content || "",
    ),
);
const noteLayoutKind = computed(() => {
  if (isWideDashboardNote.value) {
    return "dashboard";
  }
  if (editMode.value) {
    return "editor";
  }
  if (isWorkNote.value) {
    return "work";
  }
  if (isHtmlFormat.value) {
    return "research";
  }
  return "markdown";
});
let contentChangedTimeout = null;
let lastContentTap = null;
const contentEditor = ref();
const editorKey = ref(0);
const editMode = ref(false);
const editorFormat = ref("html");
const editorKind = ref("work");
const globalStore = useGlobalStore();
const isSaveChangesModalVisible = ref(false);
const isDeleteModalVisible = ref(false);
const isDraftModalVisible = ref(false);
const isNewNote = computed(() => !props.title);
const loadingIndicator = ref();
const note = ref({});
const reservedFilenameCharacters = /[<>:"/\\|?*]/;
const router = useRouter();
const newTitle = ref();
const toast = useToast();
const unsavedChanges = ref(false);
const editDoubleTapDelayMs = 420;
const editDoubleTapDistancePx = 28;

function init() {
  // Return if we already have the note e.g. When we rename a note, the route prop would change but we’d already have the note.
  if (props.title && props.title == note.value.title) {
    return;
  }

  loadingIndicator.value.setLoading();
  if (props.title) {
    getNote(props.title)
      .then((data) => {
        note.value = data;
        loadingIndicator.value.setLoaded();
      })
      .catch((error) => {
        if (error.response?.status === 404) {
          loadingIndicator.value.setFailed("Note not found", mdiNoteOffOutline);
        } else {
          loadingIndicator.value.setFailed();
          apiErrorHandler(error, toast);
        }
      });
  } else {
    newTitle.value = getInitialNewTitle();
    note.value = new Note();
    editorFormat.value = "html";
    editorKind.value = loadNewNoteKind();
    // Set the editMode to false to close any existing editors.
    // This ensures the editor is cleanly reinitialised in an empty state.
    // Simple fix for #266 without requiring a full re-work of the logic.
    editMode.value = false;
    nextTick(() => {
      editHandler();
      loadingIndicator.value.setLoaded();
    });
  }
}

function getInitialNewTitle() {
  const title = Array.isArray(props.initialTitle)
    ? props.initialTitle[0]
    : props.initialTitle;
  return String(title || "").trim();
}

// Note Editing
function toggleEditModeHandler() {
  if (editMode.value) {
    closeHandler();
  } else {
    editHandler();
  }
}

function editHandler() {
  const draftContent = loadDraft();
  if (draftContent) {
    isDraftModalVisible.value = true;
  } else {
    setEditMode();
  }
}

function setEditMode() {
  newTitle.value = isNewNote.value
    ? newTitle.value || getInitialNewTitle()
    : note.value.title;
  editorFormat.value = note.value.format || "html";
  if (editorFormat.value === "html") {
    editorKind.value = isWorkNoteHtml(note.value.content || "")
      ? "work"
      : isNewNote.value
        ? loadNewNoteKind()
        : "research";
  } else {
    editorKind.value = "markdown";
  }
  unsavedChanges.value = false;
  editMode.value = true;
}

function contentSelectionHasText() {
  const selection = window.getSelection?.();
  return Boolean(selection && !selection.isCollapsed && selection.toString());
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
  return (
    !editMode.value &&
    canModify.value &&
    !isNewNote.value &&
    !event.defaultPrevented &&
    (event.button == null || event.button === 0) &&
    (allowSelection || !contentSelectionHasText()) &&
    !isIgnoredEditTriggerTarget(event.target)
  );
}

function startEditFromContent(event, options = {}) {
  if (!canStartEditFromContent(event, options)) {
    return false;
  }

  event.preventDefault();
  editHandler();
  return true;
}

function noteContentDblClickHandler(event) {
  lastContentTap = null;
  startEditFromContent(event, { allowSelection: true });
}

function noteContentPointerUpHandler(event) {
  if (!["touch", "pen"].includes(event.pointerType)) {
    return;
  }

  if (!canStartEditFromContent(event)) {
    lastContentTap = null;
    return;
  }

  const now = window.performance?.now?.() || Date.now();
  const nextTap = {
    time: now,
    x: event.clientX,
    y: event.clientY,
  };

  const previousTap = lastContentTap;
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
  startEditFromContent(event);
}

function getInitialEditorValue() {
  const draftContent = loadDraft();
  const content = draftContent ? draftContent : note.value.content;
  if (editorFormat.value === "html" && editorKind.value === "work") {
    return content ? extractWorkMarkdown(content) : "";
  }

  return content;
}

// Note Deletion
function deleteHandler() {
  isDeleteModalVisible.value = true;
}

function deleteConfirmedHandler() {
  deleteNote(note.value.title)
    .then(() => {
      toast.add(getToastOptions("Note deleted ✓", "Success", "success"));
      router.push({ name: "home" });
    })
    .catch((error) => {
      apiErrorHandler(error, toast);
    });
}

// Note Saving
function saveHandler(close = false) {
  // Save Default Editor Mode
  saveDefaultEditorMode();

  // Empty Title Validation
  if (!newTitle.value) {
    toast.add(
      getToastOptions("Cannot save note without a title.", "Invalid", "error"),
    );
    return;
  }

  // Invalid Character Validation
  if (reservedFilenameCharacters.test(newTitle.value)) {
    badFilenameToast("Title");
    return;
  }

  // Save Note
  let newContent = getEditorContent();
  if (isNewNote.value) {
    saveNew(newTitle.value, newContent, close, editorFormat.value);
  } else {
    saveExisting(newTitle.value, newContent, close, editorFormat.value);
  }
}

function saveNew(newTitle, newContent, close = false, format = "html") {
  createNote(newTitle, newContent, format)
    .then((data) => {
      clearDraft();
      note.value = data;
      router
        .push({
          name: "note",
          params: { title: note.value.title },
        })
        .then(() => {
          // Wait for the route to be updated before setting edit mode to false
          // as the route is used to determine the action.
          noteSaveSuccess(close);
        });
    })
    .catch(noteSaveFailure);
}

function saveExisting(newTitle, newContent, close = false, format = "html") {
  // Return if no changes
  if (
    newTitle == note.value.title &&
    newContent == note.value.content &&
    format == (note.value.format || "html")
  ) {
    noteSaveSuccess(close);
    return;
  }

  updateNote(note.value.title, newTitle, newContent, format)
    .then((data) => {
      clearDraft();
      note.value = data;
      router.replace({ name: "note", params: { title: note.value.title } });
      noteSaveSuccess(close);
    })
    .catch(noteSaveFailure);
}

function updateTaskCheckboxMarkdown(content, taskIndex, checked) {
  let currentTaskIndex = 0;
  const checkboxPattern = /^(\s*(?:[-*+]|\d+[.)])\s+)\[(?: |x|X)\]/gm;
  const marker = checked ? "[x]" : "[ ]";

  const updatedContent = content.replace(checkboxPattern, (match, prefix) => {
    if (currentTaskIndex === taskIndex) {
      currentTaskIndex += 1;
      return `${prefix}${marker}`;
    }

    currentTaskIndex += 1;
    return match;
  });

  return currentTaskIndex > taskIndex ? updatedContent : null;
}

function updateTaskCheckboxHtml(content, taskIndex, checked) {
  const isFullDocument = /<(?:!doctype|html|head|body)\b/i.test(content || "");
  const parsedDocument = new DOMParser().parseFromString(
    content || "",
    "text/html",
  );
  const taskItems = [
    ...parsedDocument.body.querySelectorAll("li.task-list-item"),
  ];
  const taskItem = taskItems[taskIndex];
  if (!taskItem) {
    return null;
  }

  let checkbox = taskItem.querySelector(":scope > input[type='checkbox']");
  if (!checkbox) {
    checkbox = parsedDocument.createElement("input");
    checkbox.type = "checkbox";
    taskItem.insertBefore(checkbox, taskItem.firstChild);
  }

  if (checked) {
    checkbox.setAttribute("checked", "");
    taskItem.classList.add("checked");
    taskItem.setAttribute("data-task-checked", "true");
  } else {
    checkbox.removeAttribute("checked");
    taskItem.classList.remove("checked");
    taskItem.removeAttribute("data-task-checked");
  }

  if (isFullDocument) {
    return `<!doctype html>\n${parsedDocument.documentElement.outerHTML}`;
  }

  return parsedDocument.body.innerHTML;
}

function updateTaskCheckboxWorkHtml(content, taskIndex, checked) {
  const markdown = extractWorkMarkdown(content || "");
  const updatedMarkdown = updateTaskCheckboxMarkdown(
    markdown,
    taskIndex,
    checked,
  );
  if (updatedMarkdown == null) {
    return null;
  }

  return buildWorkNoteHtml(note.value.title, updatedMarkdown);
}

async function toggleTaskCheckbox({ index, checked }) {
  if (!canModify.value || isNewNote.value || !note.value.title) {
    throw new Error("Task checkbox changes are not available here.");
  }

  const newContent = isWorkNote.value
    ? updateTaskCheckboxWorkHtml(note.value.content || "", index, checked)
    : isHtmlFormat.value
      ? updateTaskCheckboxHtml(note.value.content || "", index, checked)
      : updateTaskCheckboxMarkdown(note.value.content || "", index, checked);

  if (newContent == null) {
    toast.add(
      getToastOptions(
        "Could not match this checkbox to the note source.",
        "Not Saved",
        "error",
      ),
    );
    throw new Error("Task checkbox source line not found.");
  }

  if (newContent === note.value.content) {
    return;
  }

  try {
    note.value = await updateNote(
      note.value.title,
      note.value.title,
      newContent,
      note.value.format || "html",
    );
    clearDraft();
  } catch (error) {
    apiErrorHandler(error, toast);
    throw error;
  }
}

function noteSaveFailure(error) {
  if (error.response?.status === 409) {
    toast.add(
      getToastOptions(
        "A note with this title already exists. Please try again with a new title.",
        "Duplicate",
        "error",
      ),
    );
  } else if (error.response?.status === 413) {
    entityTooLargeToast("note");
  } else {
    apiErrorHandler(error, toast);
  }
}

function noteSaveSuccess(close = false) {
  unsavedChanges.value = false;
  if (close) {
    closeNote();
  }
  setBeforeUnloadConfirmation(false);
  toast.add(getToastOptions("Note saved successfully ✓", "Success", "success"));
}

// Note Closure
function closeHandler() {
  if (isContentChanged()) {
    isSaveChangesModalVisible.value = true;
  } else {
    closeNote();
  }
}

function closeNote() {
  clearDraft();
  editMode.value = false;
  if (isNewNote.value) {
    router.push({ name: "home" });
  } else {
    editMode.value = false;
  }
}

// Image Upload
function addImageBlobHook(file, callback) {
  const altTextInputValue = document.getElementById(
    "toastuiAltTextInput",
  )?.value;

  // Upload the image then use the callback to insert the URL into the editor
  postAttachment(file).then(function (data) {
    if (data) {
      // If the user has entered an alt text, use it. Otherwise, use the filename returned by the API.
      const altText = altTextInputValue
        ? altTextInputValue
        : data.originalFilename || data.filename;
      callback(data.url, altText, data);
    }
  });
}

function postAttachment(file) {
  // Uploading Toast
  toast.add(getToastOptions("Uploading attachment..."));

  // Upload the attachment
  return createAttachment(file)
    .then((data) => {
      // Success Toast
      toast.add(
        getToastOptions(
          data.reused
            ? "Existing media asset reused ✓"
            : "Attachment uploaded successfully ✓",
          "Success",
          "success",
        ),
      );
      return data;
    })
    .catch((error) => {
      if (error.response?.status === 409) {
        // Note: The current implementation will append a datetime to the filename if it already exists.
        // Error Toast
        toast.add(
          getToastOptions(
            "An attachment with this filename already exists.",
            "Duplicate",
            "error",
          ),
        );
      } else if (error.response?.status == 413) {
        entityTooLargeToast("attachment");
      } else {
        apiErrorHandler(error, toast);
      }
    });
}

// Content Change Watcher
function startContentChangedTimeout() {
  clearContentChangedTimeout();
  contentChangedTimeout = setTimeout(contentChangedHandler, 1000);
}

function clearContentChangedTimeout() {
  if (contentChangedTimeout != null) {
    clearTimeout(contentChangedTimeout);
  }
}

function contentChangedHandler() {
  if (isContentChanged()) {
    unsavedChanges.value = true;
    setBeforeUnloadConfirmation(true);
    saveDraft();
  } else {
    unsavedChanges.value = false;
    setBeforeUnloadConfirmation(false);
    clearDraft();
  }
}

// Drafts
function saveDraft() {
  const content = getEditorContent();
  const userHasPersistedToken = isCurrentTokenStored();
  if (content) {
    if (userHasPersistedToken) {
      localStorage.setItem(note.value.title, content);
    } else {
      sessionStorage.setItem(note.value.title, content);
    }
  }
}

function clearDraft() {
  localStorage.removeItem(note.value.title);
  sessionStorage.removeItem(note.value.title);
}

function loadDraft() {
  const localDraft = localStorage.getItem(note.value.title);
  const sessionDraft = sessionStorage.getItem(note.value.title);
  return localDraft || sessionDraft;
}

// Keyboard Shortcuts
// 'e' to edit
Mousetrap.bind("e", () => {
  if (editMode.value === false && canModify.value) {
    editHandler();
  }
});

function keydownHandler(event) {
  // Ctrl + Enter to save
  if ((event.ctrlKey || event.metaKey) && event.key == "Enter") {
    saveHandler((close = false));
  }
  // Escape to exit edit mode
  if (event.key == "Escape") {
    closeHandler();
  }
}

// Helpers
function entityTooLargeToast(entityName) {
  toast.add(
    getToastOptions(
      `This ${entityName} is too large. Please try again with a smaller ${entityName} or adjust your server configuration.`,
      "Failure",
      "error",
    ),
  );
}

function badFilenameToast(entityName) {
  toast.add(
    getToastOptions(
      'Due to filename restrictions, the following characters are not allowed: <>:"/\\|?*',
      `Invalid ${entityName}`,
      "error",
    ),
  );
}

function setBeforeUnloadConfirmation(enable = true) {
  if (enable) {
    window.onbeforeunload = () => {
      return true;
    };
  } else {
    window.onbeforeunload = null;
  }
}

function saveDefaultEditorMode() {
  if (
    editorFormat.value !== "markdown" ||
    !contentEditor.value?.isWysiwygMode
  ) {
    return;
  }

  const isWysiwygMode = contentEditor.value.isWysiwygMode();
  localStorage.setItem(
    "defaultEditorMode",
    isWysiwygMode ? "wysiwyg" : "markdown",
  );
}

function loadDefaultEditorMode() {
  const defaultWysiwygMode = localStorage.getItem("defaultEditorMode");
  return defaultWysiwygMode || "markdown";
}

function loadNewNoteKind() {
  const key = "nirvNotesNewNoteKind";
  const legacyKey = "flatnotesNewNoteKind";
  const kind = localStorage.getItem(key) || localStorage.getItem(legacyKey);
  if (kind && !localStorage.getItem(key)) {
    localStorage.setItem(key, kind);
  }
  return kind || "work";
}

function currentNewEditorContentLooksEdited() {
  if (!contentEditor.value) {
    return false;
  }

  if (editorKind.value === "work" && contentEditor.value.getMarkdown) {
    const markdown = contentEditor.value.getMarkdown().trim();
    return Boolean(markdown);
  }

  if (editorKind.value === "research" && contentEditor.value.getContent) {
    return Boolean(contentEditor.value.getContent().trim());
  }

  return false;
}

function setNewNoteKind(kind) {
  if (kind === editorKind.value) {
    return;
  }

  if (
    currentNewEditorContentLooksEdited() &&
    !window.confirm("Switch editor mode and reset this unsaved note?")
  ) {
    return;
  }

  editorKind.value = kind;
  localStorage.setItem("nirvNotesNewNoteKind", kind);
  note.value.content =
    kind === "work" ? buildWorkNoteHtml(newTitle.value || "Untitled", "") : "";
  clearDraft();
  unsavedChanges.value = false;
  editorKey.value += 1;
}


function getNoteSourceContent() {
  return note.value.content || "";
}

function extractBodyHtml(html) {
  if (!/<(?:!doctype|html|head|body)\b/i.test(html || "")) {
    return html || "";
  }

  const parsedDocument = new DOMParser().parseFromString(
    html || "",
    "text/html",
  );
  return parsedDocument.body?.innerHTML || html || "";
}

function htmlToPlainText(html) {
  const parsedDocument = new DOMParser().parseFromString(
    extractBodyHtml(html),
    "text/html",
  );
  parsedDocument
    .querySelectorAll("script, style, template, .flatnotes-note-hidden-title")
    .forEach((element) => element.remove());

  const rawText =
    parsedDocument.body?.innerText || parsedDocument.body?.textContent || "";
  return normalizeCopiedText(rawText);
}

function normalizeCopiedText(text) {
  return String(text || "")
    .replace(/\u00a0/g, " ")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function getMarkdownSource() {
  return isWorkNote.value
    ? extractWorkMarkdown(getNoteSourceContent())
    : getNoteSourceContent();
}

function getDefaultCopyKind() {
  if (isWorkNote.value || !isHtmlFormat.value) {
    return "source";
  }
  return "text";
}

function getCopyLabel(kind) {
  if (kind === "link") {
    return "Link copied ✓";
  }
  if (kind === "html") {
    return "HTML copied ✓";
  }
  if (kind === "source") {
    return isHtmlFormat.value && !isWorkNote.value
      ? "Source copied ✓"
      : "Markdown copied ✓";
  }
  return "Text copied ✓";
}

function getNoteLink() {
  const resolved = router.resolve({
    name: "note",
    params: { title: note.value.title },
  });
  return `${window.location.origin}${resolved.href}`;
}

async function copyNote(kind = "default") {
  const copyKind = kind === "default" ? getDefaultCopyKind() : kind;
  try {
    if (copyKind === "link") {
      await writePlainTextToClipboard(getNoteLink());
    } else if (copyKind === "html") {
      const html = extractBodyHtml(getNoteSourceContent());
      await writeHtmlToClipboard(html, htmlToPlainText(html));
    } else if (copyKind === "source") {
      const source = getMarkdownSource();
      if (isWorkNote.value || !isHtmlFormat.value) {
        await writeMarkdownToClipboard(source);
      } else {
        await writePlainTextToClipboard(source);
      }
    } else {
      const text = isHtmlFormat.value
        ? htmlToPlainText(getNoteSourceContent())
        : normalizeCopiedText(getNoteSourceContent());
      await writePlainTextToClipboard(text);
    }
    toast.add(getToastOptions(getCopyLabel(copyKind), "Copied", "success"));
  } catch {
    toast.add(
      getToastOptions("Could not copy this note.", "Copy Failed", "error"),
    );
  }
}

function getCopyMenuItems() {
  if (editMode.value || isNewNote.value || !note.value.title) {
    return [];
  }

  const items = [
    {
      label:
        isWorkNote.value || !isHtmlFormat.value ? "Copy Markdown" : "Copy Text",
      icon:
        isWorkNote.value || !isHtmlFormat.value
          ? mdiCodeTags
          : mdiTextBoxOutline,
      command: () =>
        copyNote(isWorkNote.value || !isHtmlFormat.value ? "source" : "text"),
    },
  ];

  if (isHtmlFormat.value && !isWorkNote.value) {
    items.push({
      label: "Copy HTML",
      icon: mdiLanguageHtml5,
      command: () => copyNote("html"),
    });
  }

  items.push({
    label: "Copy Link",
    icon: mdiLinkVariant,
    command: () => copyNote("link"),
  });

  return items;
}

function updateNoteActions() {
  globalStore.setNoteActions([
    {
      key: "copy",
      label: "Copy",
      iconPath: mdiContentCopy,
      visible: !editMode.value && !isNewNote.value && Boolean(note.value.title),
      handler: () => copyNote(),
    },
    {
      key: "delete",
      label: "Delete",
      iconPath: mdilDelete,
      visible: canModify.value && !isNewNote.value && Boolean(note.value.title),
      handler: deleteHandler,
    },
    {
      key: "save",
      label: "Save",
      iconPath: mdilContentSave,
      visible: editMode.value,
      handler: () => saveHandler(false),
      unsaved: unsavedChanges.value,
    },
    {
      key: "edit",
      label: editMode.value ? "Done" : "Edit",
      visible: canModify.value,
      handler: toggleEditModeHandler,
    },
  ]);
  globalStore.setNoteMenuItems(getCopyMenuItems());
  globalStore.setNoteLayout({
    kind: noteLayoutKind.value,
  });
}

function isContentChanged() {
  return (
    newTitle.value != note.value.title ||
    getEditorContent() != note.value.content ||
    editorFormat.value != (note.value.format || "html")
  );
}

function getEditorContent() {
  if (!contentEditor.value) {
    return "";
  }

  if (editorFormat.value === "markdown") {
    return contentEditor.value.getMarkdown();
  }

  return contentEditor.value.getContent(newTitle.value || note.value.title);
}

watchEffect(updateNoteActions);
watch(() => props.title, init);
watch(
  () => props.initialTitle,
  () => {
    if (!isNewNote.value || unsavedChanges.value) {
      return;
    }
    newTitle.value = getInitialNewTitle();
  },
);
onMounted(init);
onUnmounted(() => globalStore.clearNoteActions());
</script>

<style scoped>
.flatnotes-note-shell,
.flatnotes-note-content {
  overflow-x: clip;
  overflow-y: visible;
}

.flatnotes-note-shell {
  width: min(100%, 68rem);
  margin-inline: auto;
}

.flatnotes-note-shell-work {
  width: min(100%, 54rem);
}

.flatnotes-note-shell-markdown {
  width: min(100%, 58rem);
}

.flatnotes-note-shell-research {
  width: min(100%, 76rem);
}

.flatnotes-note-shell-wide {
  width: min(100%, calc(100vw - 1.5rem));
  max-width: none;
  margin-inline: auto;
}


@supports not (overflow: clip) {
  .flatnotes-note-shell,
  .flatnotes-note-content {
    overflow-x: visible;
  }
}
</style>
