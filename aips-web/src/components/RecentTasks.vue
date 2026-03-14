<template>
  <details class="panel history-disclosure">
    <summary class="history-disclosure__summary">
      <div class="history-disclosure__heading">
        <p class="eyebrow">History</p>
        <div class="history-disclosure__title-row">
          <h3>最近导出</h3>
          <span v-if="items.length" class="status-badge status-badge--pending">{{ items.length }} 条</span>
        </div>
      </div>

      <div class="history-disclosure__summary-copy">
        <strong v-if="latestTask">{{ latestTask.meta.filename }}</strong>
        <strong v-else>暂时没有历史记录</strong>
        <small>{{ summaryHint }}</small>
      </div>
    </summary>

    <p v-if="missingCount" class="panel__hint panel__hint--compact">
      已自动隐藏 {{ missingCount }} 条文件已过期的历史结果。
    </p>

    <div v-if="!items.length" class="panel__hint">
      {{ missingCount ? "最近结果已过期被清理。重新处理后会回到这里。" : "还没有历史记录。处理并导出后会自动出现在这里。" }}
    </div>

    <div v-else class="history-list">
      <RouterLink
        v-for="task in items"
        :key="task.task_id"
        class="history-card"
        :to="`/result/${task.task_id}`"
      >
        <div class="history-card__row">
          <strong>{{ task.meta.filename }}</strong>
          <small>{{ task.meta.size_kb }} KB</small>
        </div>
        <p>
          {{ task.meta.width_px }} x {{ task.meta.height_px }} · {{ task.meta.format.toUpperCase() }} ·
          {{ task.meta.dpi }} DPI
        </p>
        <small>{{ task.meta.preset_name || "自定义" }}</small>
      </RouterLink>
    </div>
  </details>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { TaskSummaryResponse } from "../types";


const props = defineProps<{
  items: TaskSummaryResponse[];
  missingCount: number;
}>();

const latestTask = computed(() => props.items[0] ?? null);
const summaryHint = computed(() => {
  if (latestTask.value) {
    return `${latestTask.value.meta.width_px} x ${latestTask.value.meta.height_px} · ${latestTask.value.meta.format.toUpperCase()} · ${latestTask.value.meta.dpi} DPI`;
  }

  if (props.missingCount) {
    return "最近文件已过期，展开后可查看状态说明。";
  }

  return "默认折叠，展开后查看最近处理结果。";
});
</script>
