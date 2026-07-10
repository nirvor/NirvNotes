<template>
  <div class="flatnotes-home">
    <div class="flatnotes-home-inner">
      <SearchInput class="mb-4 shadow-[0_0_20px] shadow-theme-shadow" />
      <LoadingIndicator
        ref="loadingIndicator"
        class="flatnotes-home-pinned min-h-56"
        hideLoader
      >
        <p v-if="notes.length > 0" class="flatnotes-home-pinned-title">
          {{ globalStore.config.quickAccessTitle }}
        </p>
        <div v-if="notes.length > 0" class="flatnotes-home-pinned-list">
          <RouterLink
            v-for="note in notes.slice(0, globalStore.config.quickAccessLimit)"
            :key="note.title"
            :to="{ name: 'note', params: { title: note.title } }"
            class="flatnotes-home-pinned-link"
            :title="note.title"
          >
            {{ note.title }}
          </RouterLink>
          <RouterLink
            v-if="notes.length > globalStore.config.quickAccessLimit"
            :to="{
              name: 'search',
              query: {
                term: globalStore.config.quickAccessTerm,
                sortBy: searchSortOptions[globalStore.config.quickAccessSort],
              },
            }"
            class="flatnotes-home-pinned-link flatnotes-home-pinned-more"
            title="Show more"
            aria-label="Show more pinned notes"
          >
            <SvgIcon type="mdi" :path="mdiDotsHorizontal" size="1rem" />
          </RouterLink>
        </div>
      </LoadingIndicator>
    </div>
  </div>
</template>

<script setup>
import SvgIcon from "@jamescoyle/vue-icon";
import { mdiDotsHorizontal } from "@mdi/js";
import { useToast } from "primevue/usetoast";
import { onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";

import { apiErrorHandler, getNotes } from "../api.js";
import LoadingIndicator from "../components/LoadingIndicator.vue";
import { searchSortOptions } from "../constants.js";
import { useGlobalStore } from "../globalStore.js";
import { isCloudNetworkError } from "../desktopShell.js";
import SearchInput from "../partials/SearchInput.vue";

const globalStore = useGlobalStore();
const loadingIndicator = ref();
const notes = ref([]);
const toast = useToast();

function init() {
  if (globalStore.config.quickAccessHide) {
    return;
  }
  getNotes(
    globalStore.config.quickAccessTerm,
    globalStore.config.quickAccessSort,
    // Order by ascending if sorting by title, descending otherwise.
    globalStore.config.quickAccessSort === "title" ? "asc" : "desc",
    // Limit is increased by 1 to check if there are more notes than the limit.
    globalStore.config.quickAccessLimit + 1,
  )
    .then((data) => {
      notes.value = data;
      loadingIndicator.value.setLoaded();
    })
    .catch((error) => {
      if (isCloudNetworkError(error)) {
        notes.value = [];
        loadingIndicator.value.setLoaded();
        return;
      }
      loadingIndicator.value.setFailed();
      apiErrorHandler(error, toast);
    });
}

// Watch to allow for delayed config load.
watch(() => globalStore.config.hideRecentlyModified, init);
onMounted(init);
</script>

<style scoped>
.flatnotes-home {
  display: flex;
  min-height: 100%;
  justify-content: center;
}

.flatnotes-home-inner {
  display: flex;
  width: min(100%, 34rem);
  flex-direction: column;
  padding-top: clamp(11rem, 25vh, 18rem);
}

.flatnotes-home-pinned {
  display: flex;
  width: 100%;
  min-width: 0;
  flex-direction: column;
  align-items: stretch;
}

.flatnotes-home-pinned-title {
  margin: 0 0 0.45rem;
  color: rgb(var(--theme-text-very-muted));
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

.flatnotes-home-pinned-list {
  display: grid;
  width: 100%;
  min-width: 0;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), 1fr));
  gap: 0.36rem;
}

.flatnotes-home-pinned-link {
  min-width: 0;
  overflow: hidden;
  border: 1px solid rgb(var(--theme-border) / 0.7);
  border-radius: 999px;
  padding: 0.28rem 0.58rem;
  color: rgb(var(--theme-text-muted));
  background-color: rgb(var(--theme-background-elevated) / 0.35);
  font-size: 0.86rem;
  line-height: 1.15;
  text-align: left;
  text-decoration: none;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.flatnotes-home-pinned-link:hover,
.flatnotes-home-pinned-link:focus-visible {
  color: rgb(var(--theme-text));
  border-color: rgb(var(--theme-text-muted));
  background-color: rgb(var(--theme-background-elevated) / 0.65);
  outline: none;
}

.flatnotes-home-pinned-more {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

@media (max-width: 560px) {
  .flatnotes-home-inner {
    padding-top: clamp(10rem, 30vh, 17rem);
  }

  .flatnotes-home-pinned-list {
    grid-template-columns: 1fr;
  }
}
</style>
