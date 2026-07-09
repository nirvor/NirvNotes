import * as constants from "./constants.js";

import { Note, SearchResult } from "./classes.js";

import axios from "axios";
import { getStoredToken } from "./tokenStorage.js";
import { getToastOptions } from "./helpers.js";
import router from "./router.js";

const api = axios.create();
const noteCache = new Map();
const searchCache = new Map();
const noteCacheTtlMs = 5 * 60 * 1000;
const searchCacheTtlMs = 30 * 1000;

api.interceptors.request.use(
  // If the request is not for the token endpoint, add the token to the headers.
  function (config) {
    if (config.url !== "api/token") {
      const token = getStoredToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  function (error) {
    return Promise.reject(error);
  },
);

export function apiErrorHandler(error, toast) {
  if (error.response?.status === 401) {
    const redirectPath = router.currentRoute.value.fullPath;
    router.push({
      name: "login",
      query: { [constants.params.redirect]: redirectPath },
    });
  } else {
    console.error(error);
    toast.add(
      getToastOptions(
        "Unknown error communicating with the server. Please try again.",
        "Unknown Error",
        "error",
      ),
    );
  }
}

export function clearApiCaches() {
  noteCache.clear();
  searchCache.clear();
}

export async function getConfig() {
  try {
    const response = await api.get("api/config");
    return response.data;
  } catch (response) {
    return Promise.reject(response);
  }
}

export async function getToken(username, password, totp) {
  try {
    const response = await api.post("api/token", {
      username: username,
      password: totp ? password + totp : password,
    });
    return response.data.access_token;
  } catch (response) {
    return Promise.reject(response);
  }
}

export async function authCheck() {
  try {
    const response = await api.get("api/auth-check");
    return response.data;
  } catch (response) {
    return Promise.reject(response);
  }
}

export async function getNotes(term, sort, order, limit) {
  const cacheKey = JSON.stringify([term, sort, order, limit]);
  const cached = searchCache.get(cacheKey);
  if (cached && Date.now() - cached.loadedAt < searchCacheTtlMs) {
    return cached.data.map((note) => new SearchResult(note));
  }

  try {
    const response = await api.get("api/search", {
      params: {
        term: term,
        sort: sort,
        order: order,
        limit: limit,
      },
    });
    searchCache.set(cacheKey, {
      loadedAt: Date.now(),
      data: response.data,
    });
    return response.data.map((note) => new SearchResult(note));
  } catch (response) {
    return Promise.reject(response);
  }
}

export async function createNote(title, content, format = "html") {
  try {
    const response = await api.post("api/notes", {
      title: title,
      content: content,
      format: format,
    });
    cacheNote(response.data);
    searchCache.clear();
    return new Note(response.data);
  } catch (response) {
    return Promise.reject(response);
  }
}

export async function getNote(title) {
  const cacheKey = String(title || "");
  const cached = noteCache.get(cacheKey);
  if (cached && Date.now() - cached.loadedAt < noteCacheTtlMs) {
    return new Note({ ...cached.data });
  }

  try {
    const response = await api.get(`api/notes/${encodeURIComponent(title)}`);
    cacheNote(response.data);
    return new Note(response.data);
  } catch (response) {
    return Promise.reject(response);
  }
}

export async function getNoteContext(title) {
  try {
    const response = await api.get(
      `api/notes/${encodeURIComponent(title)}/context`,
    );
    return response.data;
  } catch (response) {
    return Promise.reject(response);
  }
}

export async function getSemanticIndex() {
  try {
    const response = await api.get("api/index");
    return response.data;
  } catch (response) {
    return Promise.reject(response);
  }
}

export async function updateNote(title, newTitle, newContent, format = "html") {
  try {
    const response = await api.patch(`api/notes/${encodeURIComponent(title)}`, {
      newTitle: newTitle,
      newContent: newContent,
      newFormat: format,
    });
    noteCache.delete(String(title || ""));
    cacheNote(response.data);
    searchCache.clear();
    return new Note(response.data);
  } catch (response) {
    return Promise.reject(response);
  }
}

export async function deleteNote(title) {
  try {
    await api.delete(`api/notes/${encodeURIComponent(title)}`);
    noteCache.delete(String(title || ""));
    searchCache.clear();
  } catch (response) {
    return Promise.reject(response);
  }
}

export async function getTags() {
  try {
    const response = await api.get("api/tags");
    return response.data;
  } catch (response) {
    return Promise.reject(response);
  }
}

function cacheNote(note) {
  if (!note?.title) {
    return;
  }

  noteCache.set(String(note.title), {
    loadedAt: Date.now(),
    data: { ...note },
  });
}

export async function createAttachment(file) {
  try {
    const formData = new FormData();
    formData.append("file", file);
    const response = await api.post("api/attachments", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data;
  } catch (response) {
    return Promise.reject(response);
  }
}
