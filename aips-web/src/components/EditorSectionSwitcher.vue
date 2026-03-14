<template>
  <nav class="section-switcher" aria-label="操作区切换">
    <button
      v-for="section in sections"
      :key="section.id"
      type="button"
      class="section-switcher__button"
      :class="{ 'section-switcher__button--active': model === section.id }"
      :aria-pressed="model === section.id"
      @click="model = section.id"
    >
      <span class="section-switcher__label">{{ section.label }}</span>
      <small class="section-switcher__summary">{{ section.summary }}</small>
    </button>
  </nav>
</template>

<script setup lang="ts">
const model = defineModel<string>({ required: true });

defineProps<{
  sections: Array<{
    id: string;
    label: string;
    summary: string;
  }>;
}>();
</script>
