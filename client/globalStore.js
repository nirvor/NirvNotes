import { defineStore } from "pinia";
import { ref } from "vue";

export const useGlobalStore = defineStore("global", () => {
  const config = ref({});
  const noteActions = ref([]);
  const noteFocusMode = ref(false);
  const noteLayoutKind = ref("default");
  const noteMenuItems = ref([]);

  function setNoteActions(actions = []) {
    noteActions.value = actions;
  }

  function setNoteMenuItems(items = []) {
    noteMenuItems.value = items;
  }

  function setNoteLayout({ focusMode = false, kind = "default" } = {}) {
    noteFocusMode.value = focusMode;
    noteLayoutKind.value = kind;
  }

  function clearNoteActions() {
    noteActions.value = [];
    noteMenuItems.value = [];
    noteFocusMode.value = false;
    noteLayoutKind.value = "default";
  }

  return {
    config,
    noteActions,
    noteFocusMode,
    noteLayoutKind,
    noteMenuItems,
    setNoteActions,
    setNoteLayout,
    setNoteMenuItems,
    clearNoteActions,
  };
});
