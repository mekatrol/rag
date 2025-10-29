<template>
  <div class="container">
    <h2 style="margin: 8px 0 16px">RAG UI</h2>
    <div class="small" style="margin-bottom: 16px">API: {{ apiBase }}</div>
    <IngestPanel />
    <ChatPanel />
  </div>
</template>

<script setup>
import IngestPanel from "./components/IngestPanel.vue";
import ChatPanel from "./components/ChatPanel.vue";
const apiBase = import.meta.env.VITE_API_BASE || "http://localhost:8000";
</script>
