<template>
  <ol class="workflow-steps">
    <li
      v-for="step in steps"
      :key="step.label"
      class="workflow-steps__item"
      :class="`workflow-steps__item--${step.status}`"
    >
      <span class="workflow-steps__index" aria-hidden="true">{{ step.index }}</span>
      <span class="workflow-steps__label">{{ step.label }}</span>
    </li>
  </ol>
</template>

<script setup lang="ts">
defineProps<{
  steps: Array<{
    index: number;
    label: string;
    status: "completed" | "current" | "pending";
  }>;
}>();
</script>
