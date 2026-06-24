import { defineStore } from "pinia";
import { ref } from "vue";

export const useGlobalStore = defineStore("global", () => {
  const config = ref({});
  const noteActions = ref([]);

  function setNoteActions(actions = []) {
    noteActions.value = actions;
  }

  function clearNoteActions() {
    noteActions.value = [];
  }

  return { config, noteActions, setNoteActions, clearNoteActions };
});
