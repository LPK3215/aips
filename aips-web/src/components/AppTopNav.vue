<template>
  <nav class="app-topnav" aria-label="主菜单">
    <div class="app-topnav__rail">
      <div class="app-topnav__meta">
        <p class="app-topnav__eyebrow">AIPS NAVIGATION</p>
        <strong class="app-topnav__title">工作区切换</strong>
        <small class="app-topnav__note">把高频操作拆成独立工作区，切页时更清楚。</small>
      </div>

      <div class="app-topnav__links">
        <RouterLink
          v-for="item in items"
          :key="item.to"
          class="app-topnav__link"
          :class="{ 'app-topnav__link--active': isActive(item.to) }"
          :to="item.to"
        >
          <span class="app-topnav__link-kicker">{{ item.kicker }}</span>
          <strong class="app-topnav__link-label">{{ item.label }}</strong>
          <small class="app-topnav__link-note">{{ item.note }}</small>
        </RouterLink>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { useRoute } from "vue-router";


const route = useRoute();
const items = [
  { to: "/", label: "证件照工作台", kicker: "Workspace", note: "单张精修、构图与导出" },
  { to: "/batch", label: "批量导出", kicker: "Batch", note: "统一参数、批量处理与导出" },
  { to: "/tools", label: "常用工具", kicker: "Tools", note: "缩放增强、单项快速处理" },
];

function isActive(target: string) {
  if (target === "/") {
    return route.path === "/";
  }

  if (target === "/tools") {
    return route.path === "/tools" || route.path.startsWith("/tools/");
  }

  return route.path === target;
}
</script>
