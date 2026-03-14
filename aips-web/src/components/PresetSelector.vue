<template>
  <section class="panel">
    <div class="panel__header">
      <div>
        <p class="eyebrow">Presets</p>
        <h3>快速套用证件照规格</h3>
      </div>
      <small>{{ presets.length }} 个模板</small>
    </div>

    <div v-if="categories.length > 1" class="preset-filters" aria-label="规格分类筛选">
      <button
        type="button"
        class="chip chip--filter"
        :class="{ 'chip--active': activeCategory === '全部' }"
        :aria-pressed="activeCategory === '全部'"
        @click="activeCategory = '全部'"
      >
        全部
      </button>
      <button
        v-for="category in categories"
        :key="category"
        type="button"
        class="chip chip--filter"
        :class="{ 'chip--active': activeCategory === category }"
        :aria-pressed="activeCategory === category"
        @click="activeCategory = category"
      >
        {{ category }}
      </button>
    </div>

    <div class="preset-grid-shell">
      <div class="preset-grid">
        <button
          v-for="preset in filteredPresets"
          :key="preset.id"
          class="preset-card"
          :class="{ 'preset-card--active': preset.id === selectedId }"
          type="button"
          @click="$emit('select', preset)"
        >
          <span class="preset-card__category">{{ preset.category }}</span>
          <strong>{{ preset.name }}</strong>
          <small>{{ preset.width }} x {{ preset.height }} {{ preset.unit }}</small>
          <p>{{ preset.description }}</p>
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";

import type { PresetItem } from "../types";


const props = defineProps<{
  presets: PresetItem[];
  selectedId: string | null;
}>();

defineEmits<{
  select: [preset: PresetItem];
}>();

const activeCategory = ref("全部");

const categories = computed(() => {
  const set = new Set(props.presets.map((preset) => preset.category).filter(Boolean));
  return Array.from(set).sort((a, b) => a.localeCompare(b));
});

const filteredPresets = computed(() => {
  if (activeCategory.value === "全部") {
    return props.presets;
  }
  return props.presets.filter((preset) => preset.category === activeCategory.value);
});

watch(categories, (next) => {
  if (activeCategory.value !== "全部" && !next.includes(activeCategory.value)) {
    activeCategory.value = "全部";
  }
});
</script>
