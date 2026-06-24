<template>
  <div class="relative w-full">
    <!-- Input -->
    <div
      class="flex w-full rounded-md border border-theme-border bg-theme-background dark:bg-theme-background-elevated"
      :class="{ 'px-3 py-2': !large, 'px-5 py-4': large }"
    >
      <IconLabel :iconPath="mdilMagnify" class="mr-2" />
      <input
        type="text"
        ref="input"
        v-model="searchTerm"
        v-focus
        class="w-full bg-transparent focus:outline-none"
        :placeholder="placeholder"
        @keydown="keydownHandler"
        @keyup="stateChangeHandler"
        @click="stateChangeHandler"
        @focus="stateChangeHandler"
        @blur="hideMenus"
        @keydown.down.prevent
        @keydown.up.prevent
      />
      <!-- Note: Default behaviour for up and down keys is prevented to stop cursor moving when tag menu is navigated. -->
    </div>

    <!-- Tag Menu -->
    <div
      v-if="tagMenuVisible"
      class="absolute z-10 mt-2 max-h-64 w-full overflow-scroll rounded-md border border-theme-border bg-theme-background p-1"
    >
      <p
        v-for="(tag, index) in tagMatches"
        ref="tagMenuItems"
        class="cursor-pointer rounded px-2 py-1 hover:bg-theme-background-elevated"
        :class="{ 'bg-theme-background-elevated': index === tagMenuIndex }"
        @click="tagChosen(tag)"
        @mousedown.prevent
      >
        <!-- Note: Default behaviour for mouse down is prevented to stop focus moving to menu on click. -->
        {{ tag }}
      </p>
    </div>

    <!-- Empty Search Tag Cloud -->
    <div
      v-if="tagCloudVisible"
      class="mt-2 w-full rounded-md border border-theme-border bg-theme-background p-3 dark:bg-theme-background-elevated"
    >
      <p class="mb-2 text-xs font-bold uppercase text-theme-text-very-muted">
        Top Tags
      </p>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="tag in topTags"
          :key="tag.name"
          type="button"
          class="rounded-full border border-theme-border bg-theme-background px-2.5 py-1 text-sm text-theme-text hover:border-theme-brand hover:text-theme-brand dark:bg-theme-background"
          @click="tagCloudChosen(tag.name)"
          @mousedown.prevent
        >
          {{ tag.name }}
          <span class="ml-1 text-theme-text-muted">{{ tag.count }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { mdilMagnify } from "@mdi/light-js";
import { useToast } from "primevue/usetoast";
import { ref, watch } from "vue";
import { useRouter } from "vue-router";

import { apiErrorHandler, getSemanticIndex, getTags } from "../api.js";
import IconLabel from "../components/IconLabel.vue";
import * as constants from "../constants.js";

const props = defineProps({
  initialSearchTerm: { type: String, default: "" },
  large: Boolean,
  placeholder: { type: String, default: "Search..." },
  showAllOnClear: Boolean,
});
const emit = defineEmits(["search"]);

const input = ref();
const router = useRouter();
const searchTerm = ref(searchTermForInput(props.initialSearchTerm));
const toast = useToast();
let tags = null;
const tagMatches = ref([]);
const tagMenuItems = ref([]);
const tagMenuIndex = ref(0);
const tagMenuVisible = ref(false);
const tagCloudVisible = ref(false);
const topTags = ref([]);
let tagCloudLoaded = false;

function searchTermForInput(value = "") {
  return value === "*" ? "" : value || "";
}

function hideMenus() {
  tagMenuVisible.value = false;
  tagCloudVisible.value = false;
}

function keydownHandler(event) {
  // Tag Menu Open
  if (tagMenuVisible.value) {
    if (event.key === "ArrowDown") {
      tagMenuIndex.value = Math.min(
        tagMenuIndex.value + 1,
        tagMatches.value.length - 1,
      );
      tagMenuItems.value[tagMenuIndex.value].scrollIntoView({
        block: "nearest",
      });
    } else if (event.key === "ArrowUp") {
      tagMenuIndex.value = Math.max(tagMenuIndex.value - 1, 0);
      tagMenuItems.value[tagMenuIndex.value].scrollIntoView({
        block: "nearest",
      });
    } else if (event.key === "Enter") {
      tagChosen(tagMatches.value[tagMenuIndex.value]);
    } else if (event.key === "Escape") {
      tagMenuVisible.value = false;
      event.stopPropagation(); // Prevent the modal from closing when the tag menu is open.
    }
  }
  // Tag Menu Closed
  else if (event.key === "Enter") {
    search();
  }
}

function tagChosen(tag) {
  replaceWordOnCursor(tag);
  tagMenuVisible.value = false;
}

function tagCloudChosen(tag) {
  searchTerm.value = `#${tag}`;
  hideMenus();
  search();
}

function search() {
  const term = searchTerm.value.trim();
  const query =
    term.length > 0
      ? { [constants.params.searchTerm]: term }
      : {
          [constants.params.searchTerm]: "*",
          [constants.params.sortBy]: constants.searchSortOptions.lastModified,
        };

  router.push({
    name: "search",
    query,
  });
  emit("search");
}

function stateChangeHandler() {
  const wordOnCursor = getWordOnCursor();
  const emptySearch = searchTerm.value.trim().length === 0;

  if (emptySearch) {
    tagMenuVisible.value = false;
    tagMatches.value = [];
    showTagCloud();
    if (props.showAllOnClear && props.initialSearchTerm !== "*") {
      router.replace({
        name: "search",
        query: {
          [constants.params.searchTerm]: "*",
          [constants.params.sortBy]: constants.searchSortOptions.lastModified,
        },
      });
    }
  } else if (wordOnCursor.charAt(0) !== "#") {
    tagMenuVisible.value = false;
    tagCloudVisible.value = false;
    tagMatches.value = [];
  } else {
    tagCloudVisible.value = false;
    // All tags are stored in lowercase, so we can do a case-insensitive search.
    filterTagMatches(wordOnCursor.toLowerCase());
  }
}

async function showTagCloud() {
  if (!tagCloudLoaded) {
    try {
      const index = await getSemanticIndex();
      const counts = new Map();
      index.forEach((note) => {
        new Set(note.tags || []).forEach((tag) => {
          counts.set(tag, (counts.get(tag) || 0) + 1);
        });
      });
      topTags.value = [...counts.entries()]
        .map(([name, count]) => ({ name, count }))
        .sort((left, right) => {
          if (right.count !== left.count) {
            return right.count - left.count;
          }
          return left.name.localeCompare(right.name);
        })
        .slice(0, 14);
    } catch (error) {
      topTags.value = [];
      apiErrorHandler(error, toast);
    }
    tagCloudLoaded = true;
  }

  tagCloudVisible.value = topTags.value.length > 0;
}

async function filterTagMatches(input) {
  if (tags === null) {
    try {
      tags = await getTags();
    } catch (error) {
      tags = [];
      apiErrorHandler(error, toast);
    }
    tags = tags.map((tag) => `#${tag}`);
  }
  const currentTagMatchCount = tagMatches.value.length;
  tagMatches.value = tags.filter(
    (tag) => tag.startsWith(input) && tag !== input,
  );
  if (
    currentTagMatchCount !== tagMatches.value.length &&
    tagMatches.value.length > 0
  ) {
    tagMenuIndex.value = 0;
    tagMenuVisible.value = true;
  } else if (tagMatches.value.length === 0) {
    tagMenuVisible.value = false;
  }
}

// Helpers

/**
 * Returns the word that the cursor is currently on.
 * @returns {Object} An object containing the start and end indices of the word.
 */
function getWordOnCursorPosition() {
  const cursorPosition = input.value.selectionStart;
  const wordStart = Math.max(
    searchTerm.value.lastIndexOf(" ", cursorPosition - 1) + 1,
    0,
  );
  let wordEnd = searchTerm.value.indexOf(" ", cursorPosition);
  if (wordEnd === -1) {
    // If there is no space after the cursor, then the word ends at the end of the input.
    wordEnd = searchTerm.value.length;
  }
  return { start: wordStart, end: wordEnd };
}

/**
 * Retrieves the word at the current cursor position in the search term.
 * @returns {string} The word at the cursor position.
 */
function getWordOnCursor() {
  const { start, end } = getWordOnCursorPosition();
  return searchTerm.value.substring(start, end);
}

/**
 * Replaces the word at the cursor position with the given replacement.
 * @param {string} replacement The word to replace the current word with.
 */
function replaceWordOnCursor(replacement) {
  const { start, end } = getWordOnCursorPosition();
  searchTerm.value =
    searchTerm.value.substring(0, start) +
    replacement +
    searchTerm.value.substring(end);
}

watch(
  () => props.initialSearchTerm,
  () => {
    searchTerm.value = searchTermForInput(props.initialSearchTerm);
  },
  { immediate: true },
);
</script>
