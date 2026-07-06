import { shallowRef } from "vue";

export const externalFileLaunch = shallowRef(null);

export function publishExternalFileLaunch(files, message = "Opened from Windows.") {
  externalFileLaunch.value = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    files,
    message,
    tone: "info",
  };
}

export function publishExternalFileLaunchError(message) {
  externalFileLaunch.value = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    files: [],
    message,
    tone: "error",
  };
}

export function supportsFileHandlingLaunchQueue() {
  return Boolean(
    "launchQueue" in window &&
      "LaunchParams" in window &&
      "files" in window.LaunchParams.prototype,
  );
}

export async function filesFromLaunchParams(launchParams) {
  const handles = launchParams.files || [];
  const files = [];
  for (const handle of handles) {
    files.push({
      file: await handle.getFile(),
      handle,
    });
  }
  return files;
}
