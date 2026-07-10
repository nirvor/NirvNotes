<template>
  <div class="relative w-full">
    <!-- Input -->
    <div
      class="flex w-full rounded-md border border-theme-border bg-theme-background dark:bg-theme-background-elevated"
      :class="{ 'px-3 py-2': !large, 'px-4 py-2.5': large }"
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
      class="absolute z-10 mt-1.5 max-h-56 w-full overflow-scroll rounded-md border border-theme-border bg-theme-background p-1"
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
    <div v-if="tagCloudVisible" class="mt-2 w-full px-1">
      <div class="flex flex-wrap gap-1.5">
        <button
          v-for="tag in topTags"
          :key="tag.name"
          type="button"
          class="inline-flex items-center gap-1 rounded-full border border-theme-border/80 bg-theme-background-elevated/60 px-2.5 py-1 text-[0.8rem] leading-none text-theme-text-muted shadow-sm transition hover:border-theme-brand hover:bg-theme-background-elevated hover:text-theme-text focus-visible:border-theme-brand focus-visible:outline-none dark:bg-theme-background-elevated/45"
          @click="tagCloudChosen(tag.name)"
          @mousedown.prevent
        >
          <IconLabel :iconPath="mdiTag" iconSize="0.8em" />
          <span>{{ tag.name }}</span>
          <span
            v-if="tag.count > 0"
            class="ml-0.5 rounded-full bg-theme-background-elevated px-1.5 py-0.5 text-[0.68rem] text-theme-text-very-muted dark:bg-theme-background"
            >{{ tag.count }}</span
          >
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { mdiTag } from "@mdi/js";
import { mdilMagnify } from "@mdi/light-js";
import { useToast } from "primevue/usetoast";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import { apiErrorHandler, getSemanticIndex, getTags } from "../api.js";
import { isCloudNetworkError } from "../desktopShell.js";
import IconLabel from "../components/IconLabel.vue";
import * as constants from "../constants.js";
import {
  getTagUsage,
  normalizeTagName,
  onTagUsageChange,
  recordTagUse,
} from "../tagUsage.js";

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
let tagCloudEntries = [];
const tagMatches = ref([]);
const tagMenuItems = ref([]);
const tagMenuIndex = ref(0);
const tagMenuVisible = ref(false);
const tagCloudVisible = ref(false);
const topTags = ref([]);
let tagCloudLoaded = false;
const tagCloudLimit = 14;
const priorityTagBonus = {
  work: 90,
  private: 70,
  infra: 60,
  pinned: 24,
};

function searchTermForInput(value = "") {
  return value === "*" ? "" : value || "";
}

function hideMenus() {
  tagMenuVisible.value = false;
  if (searchTerm.value.trim()) {
    tagCloudVisible.value = false;
  } else {
    showTagCloud();
  }
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
  const route = getRouteForSearchTerm(term);
  if (route.name === "search") {
    recordTagsFromSearchTerm(term);
  }

  router.push(route);
  emit("search");
}

function getRouteForSearchTerm(term) {
  const normalizedTerm = term.trim();
  const lowerTerm = normalizedTerm.toLowerCase();

  if (!normalizedTerm || ["*", "all", ":all"].includes(lowerTerm)) {
    return {
      name: "search",
      query: {
        [constants.params.searchTerm]: "*",
        [constants.params.sortBy]: constants.searchSortOptions.lastModified,
      },
    };
  }

  if (
    ["file", "file:", "files", "@external", "external", "open"].includes(
      lowerTerm,
    )
  ) {
    return { name: "openFile" };
  }

  const newTitle = getNewNoteTitleFromCommand(normalizedTerm);
  if (newTitle) {
    return { name: "new", query: { title: newTitle } };
  }

  return {
    name: "search",
    query: { [constants.params.searchTerm]: normalizedTerm },
  };
}

function getNewNoteTitleFromCommand(term) {
  if (term.startsWith("+")) {
    return term.slice(1).trim();
  }

  const newMatch = term.match(/^new\s+(.+)$/i);
  return newMatch ? newMatch[1].trim() : "";
}

function recordTagsFromSearchTerm(term) {
  const searchTags = [...term.matchAll(/#[a-zA-Z0-9_-]+/g)].map((match) =>
    normalizeTagName(match[0]),
  );
  recordTagUse(searchTags);
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
      const [index, indexedTags] = await Promise.all([
        getSemanticIndex(),
        getTags().catch(() => []),
      ]);
      const counts = new Map();
      const tagNames = new Set();
      index.forEach((note) => {
        new Set(note.tags || []).forEach((tag) => {
          const normalizedTag = normalizeTagName(tag);
          if (!normalizedTag) {
            return;
          }
          tagNames.add(normalizedTag);
          counts.set(normalizedTag, (counts.get(normalizedTag) || 0) + 1);
        });
      });
      indexedTags.forEach((tag) => {
        const normalizedTag = normalizeTagName(tag);
        if (normalizedTag) {
          tagNames.add(normalizedTag);
        }
      });
      tagCloudEntries = [...tagNames].map((name) => ({
        name,
        count: counts.get(name) || 0,
      }));
      rebuildTopTags();
    } catch (error) {
      topTags.value = [];
      if (!isCloudNetworkError(error)) {
        apiErrorHandler(error, toast);
      }
    }
    tagCloudLoaded = true;
  }

  rebuildTopTags();
  tagCloudVisible.value = topTags.value.length > 0;
}

function rebuildTopTags() {
  const usage = getTagUsage();
  topTags.value = tagCloudEntries
    .map((tag) => {
      const tagUsage = usage[tag.name] || { count: 0, lastUsed: 0 };
      const ageDays = tagUsage.lastUsed
        ? (Date.now() - tagUsage.lastUsed) / 86400000
        : Infinity;
      const recencyBoost = Number.isFinite(ageDays)
        ? Math.max(0, 18 - ageDays)
        : 0;
      const useBoost = Math.min(Number(tagUsage.count) || 0, 20) * 14;
      const priorityBoost = priorityTagBonus[tag.name] || 0;
      return {
        ...tag,
        score: tag.count * 10 + useBoost + recencyBoost + priorityBoost,
      };
    })
    .sort((left, right) => {
      if (right.score !== left.score) {
        return right.score - left.score;
      }
      if (right.count !== left.count) {
        return right.count - left.count;
      }
      return left.name.localeCompare(right.name);
    })
    .slice(0, tagCloudLimit);
}

async function filterTagMatches(input) {
  if (tags === null) {
    try {
      tags = await getTags();
    } catch (error) {
      tags = [];
      if (!isCloudNetworkError(error)) {
        apiErrorHandler(error, toast);
      }
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

const stopTagUsageListener = onTagUsageChange(() => {
  if (tagCloudLoaded) {
    rebuildTopTags();
  }
});

onMounted(() => {
  if (!searchTerm.value.trim()) {
    showTagCloud();
  }
});

onBeforeUnmount(stopTagUsageListener);
</script>
