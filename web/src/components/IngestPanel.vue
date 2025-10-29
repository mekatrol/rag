<template>
  <div class="card" style="margin-bottom: 16px">
    <div class="row" style="justify-content: space-between">
      <div>
        <div class="badge">Ingest documents</div>
        <div class="small">
          Reads files from the server's <code>data</code> folder
        </div>
      </div>
      <div class="row">
        <input
          class="input"
          v-model="collection"
          placeholder="collection name"
          style="width: 200px"
        />
        <button class="btn" :disabled="busy" @click="runIngest">
          {{ busy ? "Ingesting…" : "Ingest" }}
        </button>
      </div>
    </div>
    <div v-if="result" class="small" style="margin-top: 8px">{{ result }}</div>
    <div v-if="error" class="small" style="margin-top: 8px; color: #ff8a8a">
      {{ error }}
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { api } from "../api/client";

const collection = ref("docs");
const busy = ref(false);
const result = ref("");
const error = ref("");

async function runIngest() {
  busy.value = true;
  error.value = "";
  result.value = "";
  try {
    const r = await api.ingest(collection.value);
    result.value = `files: ${r.files}, chunks: ${r.chunks}`;
  } catch (e) {
    error.value = String(e);
  } finally {
    busy.value = false;
  }
}
</script>
