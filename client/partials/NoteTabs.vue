<template>
  <div class="flatnotes-note-drawer-shell print:hidden">
    <button
      v-if="showFloatingHandle"
      class="flatnotes-note-drawer-handle"
      :class="{ 'flatnotes-note-drawer-handle-open': drawerVisible }"
      type="button"
      title="Open note switcher"
      :aria-expanded="String(drawerVisible)"
      aria-controls="flatnotes-note-drawer"
      :aria-label="drawerVisible ? 'Close note switcher' : 'Open note switcher'"
      @click.stop="toggleDrawer"
    >
      <SvgIcon
        type="mdi"
        :path="drawerVisible ? mdilChevronRight : mdiBookMultipleOutline"
        size="1rem"
      />
    </button>

    <Transition name="flatnotes-note-drawer-fade">
      <div
        v-if="drawerVisible"
        class="flatnotes-note-drawer-backdrop"
        @click="closeDrawer"
      ></div>
    </Transition>

    <aside
      id="flatnotes-note-drawer"
      class="flatnotes-note-drawer"
      :class="{ 'flatnotes-note-drawer-open': drawerVisible }"
      :inert="drawerVisible ? undefined : true"
      :aria-hidden="String(!drawerVisible)"
      aria-label="Note switcher"
      @pointerdown="drawerPointerDown"
      @pointerup="drawerPointerUp"
    >
      <div class="flatnotes-note-drawer-header">
        <div>
          <div class="flatnotes-note-drawer-kicker">Notes</div>
          <div class="flatnotes-note-drawer-title">Switcher</div>
        </div>
        <button
          type="button"
          class="flatnotes-note-drawer-close"
          title="Close note switcher"
          aria-label="Close note switcher"
          @click="closeDrawer"
        >
          <SvgIcon type="mdi" :path="mdilChevronRight" size="1.05rem" />
        </button>
      </div>

      <RouterLink
        :to="allNotesRoute"
        class="flatnotes-note-drawer-primary"
        @click="closeDrawer"
      >
        <SvgIcon type="mdi" :path="mdilNoteMultiple" size="1rem" />
        <span>All notes</span>
      </RouterLink>

      <section class="flatnotes-note-drawer-section">
        <div class="flatnotes-note-drawer-section-title">Open</div>
        <div v-if="openTabs.length" class="flatnotes-note-drawer-list">
          <div
            v-for="title in openTabs"
            :key="title"
            class="flatnotes-note-drawer-row"
            :class="{ 'flatnotes-note-drawer-row-active': title === activeTitle }"
          >
            <RouterLink
              :to="{ name: 'note', params: { title } }"
              class="flatnotes-note-drawer-link"
              :title="title"
              @click="closeDrawer"
            >
              {{ title }}
            </RouterLink>
            <button
              type="button"
              class="flatnotes-note-drawer-row-close"
              title="Close tab"
              aria-label="Close tab"
              @click.stop="closeTab(title)"
            >
              x
            </button>
          </div>
        </div>
        <div v-else class="flatnotes-note-drawer-empty">No open notes</div>
      </section>

      <section class="flatnotes-note-drawer-section">
        <div class="flatnotes-note-drawer-section-title">
          <SvgIcon type="mdi" :path="mdilClock" size="0.95rem" />
          <span>Recent</span>
        </div>
        <div
          v-if="recentOptions.length"
          class="flatnotes-note-drawer-list flatnotes-note-drawer-recent-list"
        >
          <RouterLink
            v-for="title in recentOptions"
            :key="title"
            :to="{ name: 'note', params: { title } }"
            class="flatnotes-note-drawer-recent-link"
            :title="title"
            @click="closeDrawer"
          >
            {{ title }}
          </RouterLink>
        </div>
        <div v-else class="flatnotes-note-drawer-empty">No recent notes</div>
      </section>
    </aside>
  </div>
</template>

<script setup>
import SvgIcon from "@jamescoyle/vue-icon";
import { mdiBookMultipleOutline } from "@mdi/js";
import {
  mdilChevronRight,
  mdilClock,
  mdilNoteMultiple,
} from "@mdi/light-js";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { getNotes } from "../api.js";
import { params, searchSortOptions } from "../constants.js";

const maxOpenTabs = 7;
const maxRecentNotes = 14;
const serverRecentTtlMs = 60000;
const openTabsKey = "nirvNotesOpenTabs";
const recentNotesKey = "nirvNotesRecentNotes";
const legacyOpenTabsKey = "flatnotesOpenTabs";
const legacyRecentNotesKey = "flatnotesRecentNotes";

const route = useRoute();
const router = useRouter();
const openTabs = ref(loadTitles(openTabsKey, legacyOpenTabsKey));
const recentTitles = ref(loadTitles(recentNotesKey, legacyRecentNotesKey));
const serverRecentTitles = ref([]);
let serverRecentFetchedAt = 0;
let serverRecentRequest = null;
const drawerVisible = ref(false);
let edgeGesture = null;
let drawerGesture = null;

const activeTitle = computed(() =>
  route.name === "note" && route.params.title ? String(route.params.title) : "",
);

const showFloatingHandle = computed(
  () => !["note", "new", "openFile"].includes(route.name),
);

const allNotesRoute = {
  name: "search",
  query: {
    [params.searchTerm]: "*",
    [params.sortBy]: searchSortOptions.lastModified,
  },
};

const recentOptions = computed(() =>
  uniqueTitles([...recentTitles.value, ...serverRecentTitles.value]).slice(
    0,
    maxRecentNotes,
  ),
);

function loadTitles(key, legacyKey = null) {
  try {
    const storedValue = localStorage.getItem(key) || (
      legacyKey ? localStorage.getItem(legacyKey) : null
    );
    const parsed = JSON.parse(storedValue || "[]");
    if (!Array.isArray(parsed)) {
      return [];
    }

    const titles = uniqueTitles(
      parsed.filter((title) => typeof title === "string"),
    );
    if (titles.length && !localStorage.getItem(key)) {
      saveTitles(key, titles);
    }
    return titles;
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

function toggleDrawer() {
  if (drawerVisible.value) {
    closeDrawer();
  } else {
    openDrawer();
  }
}

function openDrawer() {
  drawerVisible.value = true;
  loadServerRecentTitles();
}

function closeDrawer() {
  drawerVisible.value = false;
}

function loadServerRecentTitles() {
  const now = Date.now();
  if (
    serverRecentTitles.value.length &&
    now - serverRecentFetchedAt < serverRecentTtlMs
  ) {
    return serverRecentRequest || Promise.resolve();
  }

  if (serverRecentRequest) {
    return serverRecentRequest;
  }

  serverRecentRequest = getNotes("*", "lastModified", "desc", maxRecentNotes)
    .then((notes) => {
      serverRecentTitles.value = notes.map((note) => note.title);
      serverRecentFetchedAt = Date.now();
    })
    .catch((error) => {
      console.error(error);
    })
    .finally(() => {
      serverRecentRequest = null;
    });

  return serverRecentRequest;
}

function isTouchLike(event) {
  return event.pointerType === "touch" || event.pointerType === "pen";
}

function edgePointerDown(event) {
  if (
    drawerVisible.value ||
    !isTouchLike(event) ||
    event.clientX < window.innerWidth - 34
  ) {
    return;
  }

  edgeGesture = {
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
  };
}

function edgePointerUp(event) {
  if (!edgeGesture || event.pointerId !== edgeGesture.pointerId) {
    return;
  }

  const deltaX = event.clientX - edgeGesture.startX;
  const deltaY = Math.abs(event.clientY - edgeGesture.startY);
  edgeGesture = null;

  if (deltaX <= -56 && deltaY <= 90) {
    openDrawer();
  }
}

function drawerPointerDown(event) {
  if (!drawerVisible.value || !isTouchLike(event)) {
    return;
  }

  drawerGesture = {
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
  };
}

function drawerPointerUp(event) {
  if (!drawerGesture || event.pointerId !== drawerGesture.pointerId) {
    return;
  }

  const deltaX = event.clientX - drawerGesture.startX;
  const deltaY = Math.abs(event.clientY - drawerGesture.startY);
  drawerGesture = null;

  if (deltaX >= 56 && deltaY <= 90) {
    closeDrawer();
  }
}

function keydownHandler(event) {
  if (event.key === "Escape") {
    closeDrawer();
  }
}

function pointerCancelHandler() {
  edgeGesture = null;
  drawerGesture = null;
}

function toggleDrawerEventHandler() {
  toggleDrawer();
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
    closeDrawer();
  },
);

onMounted(() => {
  window.addEventListener(
    "flatnotes:toggle-note-drawer",
    toggleDrawerEventHandler,
  );
  document.addEventListener("keydown", keydownHandler);
  document.addEventListener("pointerdown", edgePointerDown);
  document.addEventListener("pointerup", edgePointerUp);
  document.addEventListener("pointercancel", pointerCancelHandler);
});

onBeforeUnmount(() => {
  window.removeEventListener(
    "flatnotes:toggle-note-drawer",
    toggleDrawerEventHandler,
  );
  document.removeEventListener("keydown", keydownHandler);
  document.removeEventListener("pointerdown", edgePointerDown);
  document.removeEventListener("pointerup", edgePointerUp);
  document.removeEventListener("pointercancel", pointerCancelHandler);
});
</script>

<style lang="scss" scoped>
.flatnotes-note-drawer-shell {
  pointer-events: none;
}

.flatnotes-note-drawer-handle {
  position: fixed;
  top: 44%;
  right: max(0rem, env(safe-area-inset-right));
  z-index: 70;
  display: inline-flex;
  width: 2.55rem;
  height: 2.35rem;
  transform: translateY(-50%);
  align-items: center;
  justify-content: center;
  border: 1px solid rgb(var(--theme-border));
  border-right: 0;
  border-radius: 999px 0 0 999px;
  color: rgb(var(--theme-text-muted));
  background-color: rgb(var(--theme-background) / 0.86);
  box-shadow: 0 0.5rem 1.4rem rgba(0, 0, 0, 0.18);
  backdrop-filter: blur(10px);
  opacity: 1;
  pointer-events: auto;
  touch-action: manipulation;
  transition:
    background-color 120ms ease,
    border-color 120ms ease,
    color 120ms ease,
    opacity 120ms ease,
    transform 160ms ease;
}

.flatnotes-note-drawer-handle:hover,
.flatnotes-note-drawer-handle:focus-visible,
.flatnotes-note-drawer-handle-open {
  color: rgb(var(--theme-text));
  border-color: rgb(var(--theme-text-muted));
  background-color: rgb(var(--theme-background-elevated) / 0.95);
}

.flatnotes-note-drawer-handle:focus-visible {
  outline: 2px solid rgb(var(--theme-brand));
  outline-offset: 2px;
}

.flatnotes-note-drawer-handle-open {
  transform: translateY(-50%) translateX(0.35rem);
  opacity: 0;
  pointer-events: none;
}

.flatnotes-note-drawer-backdrop {
  position: fixed;
  inset: 0;
  z-index: 68;
  background-color: rgba(0, 0, 0, 0.2);
  pointer-events: auto;
}

.flatnotes-note-drawer {
  position: fixed;
  inset: 0 0 0 auto;
  z-index: 69;
  display: flex;
  width: min(15.5rem, 74vw);
  transform: translateX(100%);
  flex-direction: column;
  gap: 0.48rem;
  overflow-y: auto;
  padding: max(0.65rem, env(safe-area-inset-top)) 0.58rem
    max(0.65rem, env(safe-area-inset-bottom));
  border-left: 1px solid rgb(var(--theme-border));
  color: rgb(var(--theme-text));
  background-color: rgb(var(--theme-background) / 0.97);
  box-shadow: -0.85rem 0 2rem rgba(0, 0, 0, 0.28);
  backdrop-filter: blur(14px);
  pointer-events: auto;
  touch-action: pan-y;
  transition: transform 180ms ease;
}

.flatnotes-note-drawer-open {
  transform: translateX(0);
}

.flatnotes-note-drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.45rem;
}

.flatnotes-note-drawer-kicker,
.flatnotes-note-drawer-section-title {
  color: rgb(var(--theme-text-very-muted));
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0;
  text-transform: uppercase;
}

.flatnotes-note-drawer-title {
  font-size: 0.94rem;
  font-weight: 600;
}

.flatnotes-note-drawer-close,
.flatnotes-note-drawer-row-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  color: rgb(var(--theme-text-muted));
}

.flatnotes-note-drawer-close {
  width: 1.7rem;
  height: 1.7rem;
  border: 1px solid rgb(var(--theme-border));
  background-color: rgb(var(--theme-background-elevated));
}

.flatnotes-note-drawer-primary,
.flatnotes-note-drawer-row,
.flatnotes-note-drawer-recent-link {
  border: 1px solid rgb(var(--theme-border));
  border-radius: 6px;
  background-color: rgb(var(--theme-background-elevated));
}

.flatnotes-note-drawer-primary {
  display: inline-flex;
  min-height: 1.95rem;
  align-items: center;
  gap: 0.42rem;
  padding: 0 0.5rem;
  color: rgb(var(--theme-text));
  text-decoration: none;
}

.flatnotes-note-drawer-section {
  min-width: 0;
}

.flatnotes-note-drawer-section-title {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin-bottom: 0.2rem;
}

.flatnotes-note-drawer-list {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.22rem;
}

.flatnotes-note-drawer-recent-list {
  gap: 0.18rem;
}

.flatnotes-note-drawer-row {
  display: flex;
  min-height: 1.86rem;
  min-width: 0;
  align-items: center;
  gap: 0.25rem;
  padding: 0 0.18rem 0 0.46rem;
}

.flatnotes-note-drawer-row-active {
  border-color: rgb(var(--theme-brand));
}

.flatnotes-note-drawer-link,
.flatnotes-note-drawer-recent-link {
  min-width: 0;
  overflow: hidden;
  color: rgb(var(--theme-text-muted));
  text-overflow: ellipsis;
  white-space: nowrap;
  text-decoration: none;
}

.flatnotes-note-drawer-link {
  flex: 1 1 auto;
}

.flatnotes-note-drawer-recent-link {
  display: block;
  min-height: 1.05rem;
  padding: 0.1rem 0.36rem;
  font-size: 0.8rem;
  line-height: 1.08;
}

.flatnotes-note-drawer-row-close {
  width: 1.42rem;
  height: 1.42rem;
  flex: 0 0 auto;
  font-size: 0.76rem;
}

.flatnotes-note-drawer-primary:hover,
.flatnotes-note-drawer-primary:focus-visible,
.flatnotes-note-drawer-row:hover,
.flatnotes-note-drawer-recent-link:hover,
.flatnotes-note-drawer-recent-link:focus-visible,
.flatnotes-note-drawer-close:hover,
.flatnotes-note-drawer-close:focus-visible,
.flatnotes-note-drawer-row-close:hover,
.flatnotes-note-drawer-row-close:focus-visible {
  color: rgb(var(--theme-text));
  border-color: rgb(var(--theme-text-muted));
  background-color: rgb(var(--theme-background));
}

.flatnotes-note-drawer-empty {
  color: rgb(var(--theme-text-very-muted));
  font-size: 0.86rem;
}

.flatnotes-note-drawer-fade-enter-active,
.flatnotes-note-drawer-fade-leave-active {
  transition: opacity 140ms ease;
}

.flatnotes-note-drawer-fade-enter-from,
.flatnotes-note-drawer-fade-leave-to {
  opacity: 0;
}

@media (min-width: 768px) {
  .flatnotes-note-drawer-handle {
    top: 50%;
  }
}
</style>
