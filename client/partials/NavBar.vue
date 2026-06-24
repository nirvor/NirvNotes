<template>
  <nav class="mb-3 flex justify-end align-top md:mb-4">
    <div class="flex grow flex-wrap items-center justify-end gap-1">
      <template v-for="action in noteActions" :key="action.key">
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
      <!-- Menu -->
      <CustomButton
        :iconPath="mdilMenu"
        label="Menu"
        @click="toggleMenu"
      />
      <PrimeMenu ref="menu" :model="menuItems" :popup="true" />
    </div>
  </nav>
</template>

<script setup>
import {
  mdilLogout,
  mdilMagnify,
  mdilMenu,
  mdilMonitor,
  mdilNoteMultiple,
  mdilPlusCircle,
} from "@mdi/light-js";
import { computed, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";

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

const menuItems = [
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

const showNewButton = computed(() => {
  return globalStore.config.authType !== authTypes.readOnly;
});

const noteActions = computed(() => globalStore.noteActions);

function logOut() {
  clearStoredToken();
  localStorage.clear();
  router.push({ name: "login" });
}

function toggleMenu(event) {
  menu.value.toggle(event);
}

function showLogOutButton() {
  return ![authTypes.none, authTypes.readOnly].includes(globalStore.config.authType);
}
</script>
