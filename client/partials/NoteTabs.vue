<template>
  <div
    ref="tabsBar"
    class="mb-3 flex h-7 items-center gap-1 border-b border-theme-border pb-1 text-xs print:hidden"
  >
    <RouterLink
      :to="allNotesRoute"
      class="flex h-6 w-6 shrink-0 items-center justify-center rounded text-theme-text-muted hover:bg-theme-background-elevated"
      title="Open notes"
    >
      <SvgIcon type="mdi" :path="mdilNoteMultiple" size="1.05rem" />
    </RouterLink>

    <div class="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto">
      <div
        v-for="title in openTabs"
        :key="title"
        class="group flex h-6 max-w-40 shrink-0 items-center rounded border px-1.5"
        :class="
          title === activeTitle
            ? 'border-theme-border bg-theme-background-elevated text-theme-text'
            : 'border-transparent text-theme-text-muted hover:border-theme-border hover:bg-theme-background-elevated'
        "
      >
        <RouterLink
          :to="{ name: 'note', params: { title } }"
          class="min-w-0 truncate"
          :title="title"
        >
          {{ title }}
        </RouterLink>
        <button
          class="ml-1 rounded px-1 leading-none opacity-70 hover:bg-theme-background hover:opacity-100"
          title="Close tab"
          @click.stop="closeTab(title)"
        >
          x
        </button>
      </div>
    </div>

    <div class="relative shrink-0">
      <button
        class="flex h-6 w-6 items-center justify-center rounded text-theme-text-muted hover:bg-theme-background-elevated"
        title="Recently opened"
        @click.stop="toggleRecent"
      >
        <SvgIcon type="mdi" :path="mdilChevronDown" size="1.05rem" />
      </button>

      <div
        v-if="recentVisible"
        class="absolute right-0 top-7 z-50 max-h-64 w-56 overflow-auto rounded border border-theme-border bg-theme-background p-1 shadow-lg shadow-theme-shadow"
      >
        <RouterLink
          v-for="title in recentOptions"
          :key="title"
          :to="{ name: 'note', params: { title } }"
          class="block truncate rounded px-2 py-1 text-theme-text-muted hover:bg-theme-background-elevated hover:text-theme-text"
          :title="title"
          @click="recentVisible = false"
        >
          {{ title }}
        </RouterLink>
        <div
          v-if="recentOptions.length === 0"
          class="px-2 py-1 text-theme-text-very-muted"
        >
          No recent notes
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import SvgIcon from "@jamescoyle/vue-icon";
import { mdilChevronDown, mdilNoteMultiple } from "@mdi/light-js";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { getNotes } from "../api.js";
import { params, searchSortOptions } from "../constants.js";

const maxOpenTabs = 7;
const maxRecentNotes = 14;
const openTabsKey = "flatnotesOpenTabs";
const recentNotesKey = "flatnotesRecentNotes";

const route = useRoute();
const router = useRouter();
const openTabs = ref(loadTitles(openTabsKey));
const recentTitles = ref(loadTitles(recentNotesKey));
const serverRecentTitles = ref([]);
const recentVisible = ref(false);
const tabsBar = ref();

const activeTitle = computed(() =>
  route.name === "note" && route.params.title ? String(route.params.title) : "",
);

const allNotesRoute = {
  name: "search",
  query: {
    [params.searchTerm]: "*",
    [params.sortBy]: searchSortOptions.title,
  },
};

const recentOptions = computed(() =>
  uniqueTitles([...recentTitles.value, ...serverRecentTitles.value]).slice(
    0,
    maxRecentNotes,
  ),
);

function loadTitles(key) {
  try {
    const parsed = JSON.parse(localStorage.getItem(key) || "[]");
    if (!Array.isArray(parsed)) {
      return [];
    }

    return uniqueTitles(parsed.filter((title) => typeof title === "string"));
  } catch {
    return [];
  }
}

function saveTitles(key, titles) {
  localStorage.setItem(key, JSON.stringify(uniqueTitles(titles)));
}

function uniqueTitles(titles) {
  return [...new Set(titles.map((title) => title.trim()).filter(Boolean))];
}

function rememberTitle(title) {
  const open = uniqueTitles([
    title,
    ...openTabs.value.filter((existingTitle) => existingTitle !== title),
  ]).slice(0, maxOpenTabs);

  const recent = uniqueTitles([
    title,
    ...recentTitles.value.filter((existingTitle) => existingTitle !== title),
  ]).slice(0, maxRecentNotes);

  openTabs.value = open;
  recentTitles.value = recent;
  saveTitles(openTabsKey, open);
  saveTitles(recentNotesKey, recent);
}

function closeTab(title) {
  const wasActive = title === activeTitle.value;
  const nextTabs = openTabs.value.filter(
    (existingTitle) => existingTitle !== title,
  );
  openTabs.value = nextTabs;
  saveTitles(openTabsKey, nextTabs);

  if (!wasActive) {
    return;
  }

  const nextTitle = nextTabs[0];
  if (nextTitle) {
    router.push({ name: "note", params: { title: nextTitle } });
  } else {
    router.push({ name: "home" });
  }
}

function toggleRecent() {
  recentVisible.value = !recentVisible.value;
  if (recentVisible.value) {
    loadServerRecentTitles();
  }
}

function loadServerRecentTitles() {
  getNotes("*")
    .then((notes) => {
      serverRecentTitles.value = notes
        .sort((a, b) => b.lastModified - a.lastModified)
        .map((note) => note.title)
        .slice(0, maxRecentNotes);
    })
    .catch((error) => {
      console.error(error);
    });
}

function closeRecentOnOutsideClick(event) {
  if (!tabsBar.value?.contains(event.target)) {
    recentVisible.value = false;
  }
}

watch(
  activeTitle,
  (title) => {
    if (title) {
      rememberTitle(title);
    }
  },
  { immediate: true },
);

watch(
  () => route.fullPath,
  () => {
    recentVisible.value = false;
  },
);

onMounted(() => {
  document.addEventListener("click", closeRecentOnOutsideClick);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", closeRecentOnOutsideClick);
});
</script>
