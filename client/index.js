import App from "/App.vue";
import PrimeVue from "primevue/config";
import ToastService from "primevue/toastservice";
import { createApp } from "vue";
import { createPinia } from "pinia";
import {
  filesFromLaunchParams,
  filesFromNativePayloads,
  publishExternalFileLaunch,
  publishExternalFileLaunchError,
  supportsFileHandlingLaunchQueue,
  supportsNativeFileBridge,
} from "./externalFiles.js";
import { loadStoredToken } from "./tokenStorage.js";
import router from "/router.js";

const app = createApp(App);
const pinia = createPinia();

app.use(router);
app.use(pinia);
app.use(PrimeVue, { unstyled: true });
app.use(ToastService);

// Custom v-focus directive to focus on an element when mounted
app.directive("focus", {
  mounted(el) {
    el.focus();
  },
});

loadStoredToken();

app.mount("#app");

let nativeHostInitialized = false;

async function publishNativeFiles(payloads, message) {
  const files = filesFromNativePayloads(payloads || []);
  if (!files.length) {
    return false;
  }

  publishExternalFileLaunch(files, message || "Opened from NirvNotes client.");
  await router.push({ name: "openFile" }).catch(() => {});
  return true;
}

async function consumeNativeLaunchFiles() {
  if (!supportsNativeFileBridge()) {
    return;
  }

  document.body.classList.add("nirvnotes-native-host");
  try {
    const payloads = await window.pywebview.api.consume_launch_files();
    await publishNativeFiles(payloads, "Opened from Windows client.");
  } catch (error) {
    publishExternalFileLaunchError("Could not read the local file.");
    await router.push({ name: "openFile" }).catch(() => {});
    console.error(error);
  }
}

async function openNativeFilesFromDialog() {
  if (!supportsNativeFileBridge()) {
    return;
  }

  try {
    const payloads = await window.pywebview.api.open_local_files();
    await publishNativeFiles(payloads, "Loaded from Windows client.");
  } catch (error) {
    publishExternalFileLaunchError("Could not open the local file.");
    await router.push({ name: "openFile" }).catch(() => {});
    console.error(error);
  }
}

function syncWindowControlsOverlayClass() {
  const overlay = navigator.windowControlsOverlay;
  document.body.classList.toggle(
    "flatnotes-window-controls-overlay",
    Boolean(overlay?.visible),
  );
}

if ("windowControlsOverlay" in navigator) {
  syncWindowControlsOverlayClass();
  navigator.windowControlsOverlay.addEventListener(
    "geometrychange",
    syncWindowControlsOverlayClass,
  );
}

window.addEventListener(
  "nirvnotes:open-native-file-dialog",
  openNativeFilesFromDialog,
);

function initializeNativeHost() {
  if (nativeHostInitialized || !supportsNativeFileBridge()) {
    return;
  }

  nativeHostInitialized = true;
  consumeNativeLaunchFiles();
}

function scheduleNativeHostInitialization() {
  window.setTimeout(initializeNativeHost, 250);
}

window.addEventListener("pywebviewready", scheduleNativeHostInitialization, {
  once: true,
});

if (supportsNativeFileBridge()) {
  document.body.classList.add("nirvnotes-native-host");
  window.addEventListener("load", scheduleNativeHostInitialization, {
    once: true,
  });
}

if (supportsFileHandlingLaunchQueue()) {
  window.launchQueue.setConsumer(async (launchParams) => {
    try {
      const files = await filesFromLaunchParams(launchParams);
      if (!files.length) {
        return;
      }

      publishExternalFileLaunch(files, "Opened from Windows.");
      await router.push({ name: "openFile" }).catch(() => {});
    } catch (error) {
      publishExternalFileLaunchError("Could not read the file from Windows.");
      await router.push({ name: "openFile" }).catch(() => {});
      console.error(error);
    }
  });
}

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  });
}
