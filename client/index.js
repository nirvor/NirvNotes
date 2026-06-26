import App from "/App.vue";
import PrimeVue from "primevue/config";
import ToastService from "primevue/toastservice";
import { createApp } from "vue";
import { createPinia } from "pinia";
import {
  filesFromLaunchParams,
  publishExternalFileLaunch,
  publishExternalFileLaunchError,
  supportsFileHandlingLaunchQueue,
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
