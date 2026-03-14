<template>
  <details class="panel info-disclosure" :open="defaultOpen">
    <summary class="info-disclosure__summary">
      <div class="info-disclosure__heading">
        <p class="eyebrow">{{ eyebrow }}</p>
        <div class="info-disclosure__title-row">
          <h3>{{ title }}</h3>
          <span
            v-if="statusLabel"
            class="status-badge"
            :class="statusTone ? `status-badge--${statusTone}` : ''"
          >
            {{ statusLabel }}
          </span>
        </div>
      </div>
      <div class="info-disclosure__summary-copy">
        <strong>{{ summary }}</strong>
        <small>{{ hint }}</small>
      </div>
    </summary>

    <dl class="info-disclosure__grid">
      <div v-for="item in items" :key="item.label">
        <dt>{{ item.label }}</dt>
        <dd>{{ item.value }}</dd>
      </div>
    </dl>
  </details>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    eyebrow: string;
    title: string;
    summary: string;
    hint?: string;
    defaultOpen?: boolean;
    statusLabel?: string;
    statusTone?: "warning" | "success" | "pending";
    items: Array<{
      label: string;
      value: string;
    }>;
  }>(),
  {
    hint: "点击展开查看完整信息",
    defaultOpen: false,
  },
);
</script>
