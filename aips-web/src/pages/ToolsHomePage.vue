<template>
  <main class="app-shell">
    <AppTopNav />

    <section class="hero hero--compact">
      <div class="hero__copy">
        <p class="eyebrow">TOOLS</p>
        <h1>常用处理，</h1>
        <h1>拆开单独做。</h1>
        <p class="hero__lede">
          把缩放、增强这类单项操作拆开，按明确目标直接处理。
        </p>
      </div>
      <div class="hero__badge">
        <span>图片缩放</span>
        <span>清晰增强</span>
        <span>独立页面操作</span>
      </div>
    </section>

    <section class="tool-grid">
      <RouterLink class="tool-card" to="/tools/resize">
        <p class="tool-card__eyebrow">Resize</p>
        <h3>图片缩放</h3>
        <p>适合放大、缩小、统一尺寸、改头像分辨率。支持锁定比例和快速倍数。</p>
        <small>常见场景：投稿尺寸、平台上传、社媒头像、打印前统一尺寸。</small>
      </RouterLink>

      <RouterLink class="tool-card" to="/tools/enhance">
        <p class="tool-card__eyebrow">Enhance</p>
        <h3>清晰增强</h3>
        <p>适合轻度模糊、轻噪点、画面发灰的图片。支持放大、去噪、锐化和对比度提升。</p>
        <small>边界说明：这是常规增强，不承诺重度去马赛克或专业级 AI 修复。</small>
      </RouterLink>
    </section>
  </main>
</template>

<script setup lang="ts">
import AppTopNav from "../components/AppTopNav.vue";
</script>
