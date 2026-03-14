import { createRouter, createWebHistory } from "vue-router";

import BatchPage from "../pages/BatchPage.vue";
import EnhanceToolPage from "../pages/EnhanceToolPage.vue";
import ResultPage from "../pages/ResultPage.vue";
import ResizeToolPage from "../pages/ResizeToolPage.vue";
import ToolsHomePage from "../pages/ToolsHomePage.vue";
import WorkbenchPage from "../pages/WorkbenchPage.vue";


const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "workbench",
      component: WorkbenchPage,
    },
    {
      path: "/batch",
      name: "batch",
      component: BatchPage,
    },
    {
      path: "/tools",
      name: "tools",
      component: ToolsHomePage,
    },
    {
      path: "/tools/resize",
      name: "tool-resize",
      component: ResizeToolPage,
    },
    {
      path: "/tools/enhance",
      name: "tool-enhance",
      component: EnhanceToolPage,
    },
    {
      path: "/result/:taskId",
      name: "result",
      component: ResultPage,
      props: true,
    },
  ],
});

export default router;
