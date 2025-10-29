<template>
  <div class="card">
    <div class="badge">Ask questions</div>
    <div class="row" style="margin-top: 8px">
      <input
        class="input"
        v-model="q"
        placeholder="Ask about the ingested documents"
        @keydown.enter="ask"
      />
      <button class="btn" :disabled="busy || !q.trim()" @click="ask">
        {{ busy ? "Asking…" : "Ask" }}
      </button>
    </div>
    <div class="small" style="margin-top: 8px">
      Top K
      <input
        class="input"
        type="number"
        min="1"
        max="10"
        v-model.number="topK"
        style="width: 72px; display: inline-block; margin-left: 6px"
      />
      Collection
      <input
        class="input"
        v-model="collection"
        style="width: 160px; display: inline-block; margin-left: 6px"
      />
    </div>

    <div v-if="answer" class="pre" style="margin-top: 12px">{{ answer }}</div>

    <details v-if="contexts.length" style="margin-top: 12px">
      <summary class="small">Contexts ({{ contexts.length }})</summary>
      <ul>
        <li v-for="(c, i) in contexts" :key="i">
          <span class="small"
            >{{ c.path }} #{{ c.chunk_index }} · score
            {{ c.score?.toFixed(3) }}</span
          >
          <div class="small pre">{{ c.text }}</div>
        </li>
      </ul>
    </details>

    <div v-if="error" class="small" style="margin-top: 8px; color: #ff8a8a">
      {{ error }}
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { api } from "../api/client";

const q = ref("");
const topK = ref(4);
const collection = ref("docs");
const busy = ref(false);
const error = ref("");
const answer = ref("");
const contexts = ref([]);

async function ask() {
  if (!q.value.trim()) return;
  busy.value = true;
  error.value = "";
  answer.value = "";
  contexts.value = [];
  try {
    const r = await api.query(q.value, topK.value, collection.value);
    answer.value = r.answer || "";
    contexts.value = r.contexts || [];
  } catch (e) {
    error.value = String(e);
  } finally {
    busy.value = false;
  }
}
</script>
