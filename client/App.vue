<template>
  <LoadingIndicator
    ref="loadingIndicator"
    class="flatnotes-app-shell container mx-auto flex min-h-screen w-full min-w-0 max-w-full flex-col px-1.5 py-3 print:max-w-full"
    :class="{
      'flatnotes-app-shell-note': route.name === 'note' || route.name === 'new',
      'flatnotes-app-shell-dashboard': isDashboardRoute,
      'flatnotes-app-shell-note-work':
        isNoteRoute && globalStore.noteLayoutKind === 'work',
      'flatnotes-app-shell-note-research':
        isNoteRoute && globalStore.noteLayoutKind === 'research',
      'flatnotes-app-shell-note-markdown':
        isNoteRoute && globalStore.noteLayoutKind === 'markdown',
    }"
  >
    <PrimeToast />
    <SearchModal v-model="isSearchModalVisible" />
    <NavBar
      v-if="showNavBar"
      ref="navBar"
      :class="{
        'print:hidden': route.name == 'note',
      }"
      @toggleSearchModal="toggleSearchModal"
    />
    <NoteTabs v-if="showNavBar" />
    <RouterView />
  </LoadingIndicator>
</template>

<script setup>
import Mousetrap from "mousetrap";
import "mousetrap/plugins/global-bind/mousetrap-global-bind";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, ref } from "vue";
import { RouterView, useRoute } from "vue-router";

import { apiErrorHandler, getConfig } from "./api.js";
import PrimeToast from "./components/PrimeToast.vue";
import { useGlobalStore } from "./globalStore.js";
import { loadTheme } from "./helpers.js";
import NavBar from "./partials/NavBar.vue";
import NoteTabs from "./partials/NoteTabs.vue";
import SearchModal from "./partials/SearchModal.vue";
import LoadingIndicator from "./components/LoadingIndicator.vue";
import router from "./router.js";

const globalStore = useGlobalStore();
const isSearchModalVisible = ref(false);
const loadingIndicator = ref();
const navBar = ref();
const route = useRoute();
const toast = useToast();

// '/' to search
Mousetrap.bind("/", () => {
  if (route.name !== "login") {
    toggleSearchModal();
    return false;
  }
});

// 'CTRL + ALT/OPT + N' to create new note
Mousetrap.bindGlobal("ctrl+alt+n", () => {
  if (route.name !== "login") {
    router.push({ name: "new" });
    return false;
  }
});

// 'CTRL + ALT/OPT + H' to go to home
Mousetrap.bindGlobal("ctrl+alt+h", () => {
  if (route.name !== "login") {
    router.push({ name: "home" });
    return false;
  }
});

onMounted(loadInitialConfig);

function loadInitialConfig() {
  getConfig()
    .then((data) => {
      globalStore.config = data;
      loadingIndicator.value?.setLoaded();
      warmCommonNoteViews();
    })
    .catch((error) => {
      apiErrorHandler(error, toast);
      loadingIndicator.value?.setFailed();
    });
}

const showNavBar = computed(() => {
  return route.name !== "login";
});

const isNoteRoute = computed(
  () => route.name === "note" || route.name === "new",
);

const isDashboardRoute = computed(() => {
  if (route.name !== "note") {
    return false;
  }
  const title = normalizeNoteTitle(route.params.title);
  return (
    title === "nirv-bot" ||
    title === "nirv bot status" ||
    title.startsWith("nirv bot ") ||
    title.startsWith("nirv-bot ")
  );
});

function normalizeNoteTitle(value) {
  const raw = Array.isArray(value) ? value[0] : value;
  const text = String(raw || "");
  try {
    return decodeURIComponent(text).trim().toLowerCase().replace(/\s+/g, " ");
  } catch {
    return text.trim().toLowerCase().replace(/\s+/g, " ");
  }
}

function toggleSearchModal() {
  isSearchModalVisible.value = !isSearchModalVisible.value;
}

function warmCommonNoteViews() {
  const run = () => {
    void Promise.all([
      import("./components/html/HtmlViewer.vue"),
      import("./components/toastui/ToastViewer.vue"),
      import("./components/work/WorkNoteViewer.vue"),
      import("./components/toastui/renderEnhancements.js"),
    ]).catch(() => {});
  };

  if ("requestIdleCallback" in window) {
    if (
      window.pywebview ||
      document.body.classList.contains("nirvnotes-native-host")
    ) {
      window.setTimeout(run, 450);
      return;
    }
    window.requestIdleCallback(run, { timeout: 2200 });
  } else {
    window.setTimeout(run, 900);
  }
}

loadTheme();
</script>

<style scoped>
.flatnotes-app-shell {
  overflow: visible;
}

.flatnotes-app-shell-note {
  max-width: min(100%, 68rem);
}

.flatnotes-app-shell-note-work {
  max-width: min(100%, 54rem);
}

.flatnotes-app-shell-note-markdown {
  max-width: min(100%, 58rem);
}

.flatnotes-app-shell-note-research {
  max-width: min(100%, 76rem);
}

.flatnotes-app-shell-dashboard,
.flatnotes-app-shell-note.flatnotes-app-shell-dashboard {
  width: min(100%, calc(100vw - 1.5rem));
  max-width: none;
}
</style>
