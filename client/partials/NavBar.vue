<template>
  <nav class="mb-2 flex justify-end align-top md:mb-3">
    <div
      class="flatnotes-navbar-actions flex grow flex-wrap items-center justify-end gap-1"
    >
      <template v-for="action in leadingNoteActions" :key="action.key">
        <CustomButton
          v-if="action.visible !== false"
          :label="action.label"
          :iconPath="action.iconPath"
          :style="action.style || 'subtle'"
          class="relative"
          @click="action.handler"
        >
          <div
            v-if="action.unsaved"
            class="absolute right-1 top-1 h-1.5 w-1.5 rounded-full bg-theme-brand"
          ></div>
        </CustomButton>
      </template>
      <!-- New Note -->
      <RouterLink v-if="showNewButton" :to="{ name: 'new' }">
        <CustomButton :iconPath="mdilPlusCircle" label="New Note" />
      </RouterLink>
      <!-- Note Switcher -->
      <CustomButton
        v-if="showNoteSwitcherButton"
        :iconPath="mdiBookMultipleOutline"
        label="Notes"
        class="flatnotes-navbar-icon-only"
        @click="toggleNoteDrawer"
      />
      <!-- Menu -->
      <CustomButton :iconPath="mdilMenu" label="Menu" @click="toggleMenu" />
      <PrimeMenu ref="menu" :model="menuItems" :popup="true" />
      <template v-for="action in trailingNoteActions" :key="action.key">
        <CustomButton
          v-if="action.visible !== false"
          :label="action.label"
          :iconPath="action.iconPath"
          :style="action.style || 'subtle'"
          class="relative"
          :class="{ 'flatnotes-navbar-icon-only': action.iconOnly }"
          @click="action.handler"
        >
          <div
            v-if="action.unsaved"
            class="absolute right-1 top-1 h-1.5 w-1.5 rounded-full bg-theme-brand"
          ></div>
        </CustomButton>
      </template>
    </div>
  </nav>
</template>

<script setup>
import { mdiBookMultipleOutline } from "@mdi/js";
import {
  mdilLogout,
  mdilMagnify,
  mdilMenu,
  mdilMonitor,
  mdilNoteMultiple,
  mdilPlusBox,
  mdilPlusCircle,
} from "@mdi/light-js";
import { computed, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";

import { clearApiCaches } from "../api.js";
import CustomButton from "../components/CustomButton.vue";
import PrimeMenu from "../components/PrimeMenu.vue";
import { authTypes, params, searchSortOptions } from "../constants.js";
import { useGlobalStore } from "../globalStore.js";
import { toggleTheme } from "../helpers.js";
import { clearStoredToken } from "../tokenStorage.js";

const globalStore = useGlobalStore();
const menu = ref();
const router = useRouter();

const emit = defineEmits(["toggleSearchModal"]);

const baseMenuItems = [
  {
    label: "New Window",
    icon: mdilPlusBox,
    command: openNewWindow,
  },
  {
    separator: true,
  },
  {
    label: "Search",
    icon: mdilMagnify,
    command: () => emit("toggleSearchModal"),
    keyboardShortcut: "/",
  },
  {
    label: "All Notes",
    icon: mdilNoteMultiple,
    command: () =>
      router.push({
        name: "search",
        query: {
          [params.searchTerm]: "*",
          [params.sortBy]: searchSortOptions.lastModified,
        },
      }),
  },
  {
    label: "Toggle Theme",
    icon: mdilMonitor,
    command: toggleTheme,
  },
  {
    separator: true,
    visible: showLogOutButton,
  },
  {
    label: "Log Out",
    icon: mdilLogout,
    command: logOut,
    visible: showLogOutButton,
  },
];

const menuItems = computed(() => {
  const noteItems = globalStore.noteMenuItems || [];
  if (!noteItems.length) {
    return baseMenuItems;
  }

  return [...noteItems, { separator: true }, ...baseMenuItems];
});

const showNewButton = computed(() => {
  return globalStore.config.authType !== authTypes.readOnly;
});

const noteActions = computed(() => globalStore.noteActions || []);

const leadingNoteActions = computed(() =>
  noteActions.value.filter((action) => action.placement !== "end"),
);

const trailingNoteActions = computed(() =>
  noteActions.value.filter((action) => action.placement === "end"),
);

const showNoteSwitcherButton = computed(() => {
  return globalStore.config.authType != null;
});

function logOut() {
  clearApiCaches();
  clearStoredToken();
  localStorage.clear();
  router.push({ name: "login" });
}

function toggleMenu(event) {
  menu.value.toggle(event);
}

function toggleNoteDrawer() {
  window.dispatchEvent(new CustomEvent("flatnotes:toggle-note-drawer"));
}

function openNewWindow() {
  const targetRoute = router.currentRoute.value.name === "openFile"
    ? router.resolve({ name: "home" })
    : router.resolve(router.currentRoute.value.fullPath || { name: "home" });
  window.open(targetRoute.href, "_blank", "noopener");
}

function showLogOutButton() {
  return ![authTypes.none, authTypes.readOnly].includes(
    globalStore.config.authType,
  );
}
</script>

<style scoped>
@media (max-width: 560px) {
  .flatnotes-navbar-actions {
    gap: 0.12rem;
  }

  .flatnotes-navbar-actions :deep(.flatnotes-custom-button) {
    min-width: 1.75rem;
    padding-inline: 0.42rem;
  }

  .flatnotes-navbar-actions :deep(.flatnotes-icon-label-text) {
    display: none;
  }

  .flatnotes-navbar-actions :deep(.flatnotes-icon-label-icon) {
    margin-right: 0 !important;
  }
}

.flatnotes-navbar-actions :deep(.flatnotes-navbar-icon-only) {
  display: inline-flex;
  min-width: 1.78rem;
  align-items: center;
  justify-content: center;
  padding-inline: 0.42rem;
}

.flatnotes-navbar-actions
  :deep(.flatnotes-navbar-icon-only .flatnotes-icon-label-text) {
  display: none;
}

.flatnotes-navbar-actions
  :deep(.flatnotes-navbar-icon-only .flatnotes-icon-label-icon) {
  margin-right: 0 !important;
}
</style>
