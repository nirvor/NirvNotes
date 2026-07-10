import { shallowRef } from "vue";

export const externalFileLaunch = shallowRef(null);

export function publishExternalFileLaunch(
  files,
  message = "Opened from Windows.",
) {
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

export function supportsNativeFileBridge() {
  return Boolean(window.pywebview?.api);
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

export function filesFromNativePayloads(payloads = []) {
  return payloads
    .filter((payload) => payload && typeof payload.content === "string")
    .map((payload) => ({
      file: new File([payload.content], payload.name || "external.txt", {
        type: payload.type || "text/plain",
        lastModified: payload.lastModified || Date.now(),
      }),
      handle: payload.writable ? nativeWritableHandle(payload) : null,
    }));
}

function nativeWritableHandle(payload) {
  async function getFile() {
    return new File([payload.content || ""], payload.name || "external.txt", {
      type: payload.type || "text/plain",
      lastModified: payload.lastModified || Date.now(),
    });
  }

  return {
    id: payload.id,
    name: payload.name,
    getFile,
    queryPermission: async () => "granted",
    requestPermission: async () => "granted",
    createWritable: async () => {
      const chunks = [];
      return {
        write: async (content) => {
          if (content instanceof Blob) {
            chunks.push(await content.text());
            return;
          }
          chunks.push(String(content ?? ""));
        },
        close: async () => {
          const nextContent = chunks.join("");
          const savedPayload = await window.pywebview.api.save_native_file(
            payload.id,
            nextContent,
          );
          payload.content = nextContent;
          payload.size = savedPayload?.size ?? new Blob([nextContent]).size;
          payload.lastModified = savedPayload?.lastModified || Date.now();
        },
      };
    },
  };
}
