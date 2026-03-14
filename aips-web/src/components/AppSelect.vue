<template>
  <div
    ref="rootRef"
    class="app-select"
    :class="{
      'app-select--open': open,
      'app-select--above': menuDirection === 'above',
      'app-select--disabled': disabled,
    }"
  >
    <button
      ref="triggerRef"
      class="app-select__trigger"
      type="button"
      :disabled="disabled"
      :aria-controls="open ? listboxId : undefined"
      :aria-expanded="open"
      aria-haspopup="listbox"
      @click="toggleOpen"
      @keydown="handleTriggerKeydown"
    >
      <span class="app-select__label">{{ selectedOption?.label ?? placeholder }}</span>
      <span v-if="selectedOption?.description" class="app-select__description">
        {{ selectedOption.description }}
      </span>
      <span class="app-select__chevron" aria-hidden="true"></span>
    </button>

    <Teleport to="body">
      <div v-if="open" class="app-select__portal">
        <div ref="menuShellRef" class="app-select__menu-shell" :style="menuStyle">
          <ul
            :id="listboxId"
            ref="listRef"
            class="app-select__menu"
            role="listbox"
            tabindex="-1"
            :aria-activedescendant="highlightedOptionId"
            @keydown="handleListKeydown"
          >
            <li v-for="(option, index) in options" :key="option.value" class="app-select__item">
              <button
                :id="optionId(index)"
                class="app-select__option"
                :class="{
                  'app-select__option--active': option.value === model,
                  'app-select__option--highlighted': index === highlightedIndex,
                }"
                :data-index="index"
                type="button"
                role="option"
                :aria-selected="option.value === model"
                @click="selectOption(option.value)"
                @mousemove="highlightedIndex = index"
              >
                <span class="app-select__option-copy">
                  <span class="app-select__option-label">{{ option.label }}</span>
                  <small v-if="option.description" class="app-select__option-description">
                    {{ option.description }}
                  </small>
                </span>
                <span v-if="option.value === model" class="app-select__option-check" aria-hidden="true">已选</span>
              </button>
            </li>
          </ul>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";


type SelectOption = {
  value: string;
  label: string;
  description?: string;
};

const model = defineModel<string>({ required: true });

const props = withDefaults(
  defineProps<{
    options: readonly SelectOption[];
    placeholder?: string;
    disabled?: boolean;
  }>(),
  {
    placeholder: "请选择",
    disabled: false,
  },
);

const selectUid = `app-select-${Math.random().toString(36).slice(2, 10)}`;
const listboxId = `${selectUid}-listbox`;
const open = ref(false);
const highlightedIndex = ref(0);
const menuDirection = ref<"below" | "above">("below");
const menuStyle = ref<Record<string, string>>({});
const rootRef = ref<HTMLElement | null>(null);
const triggerRef = ref<HTMLButtonElement | null>(null);
const menuShellRef = ref<HTMLElement | null>(null);
const listRef = ref<HTMLElement | null>(null);

const selectedOption = computed(() => props.options.find((option) => option.value === model.value) ?? null);
const highlightedOptionId = computed(() => optionId(highlightedIndex.value));

function optionId(index: number) {
  return `${selectUid}-option-${index}`;
}

function syncHighlightedIndex() {
  const selectedIndex = props.options.findIndex((option) => option.value === model.value);
  highlightedIndex.value = selectedIndex >= 0 ? selectedIndex : 0;
}

function closeMenu() {
  open.value = false;
}

function updateMenuPosition() {
  const trigger = triggerRef.value;
  if (!trigger) {
    return;
  }

  const viewportPadding = 12;
  const gap = 10;
  const rect = trigger.getBoundingClientRect();
  const width = Math.min(Math.max(rect.width, 220), window.innerWidth - viewportPadding * 2);
  const estimatedHeight =
    listRef.value?.offsetHeight ?? Math.min(320, Math.max(180, props.options.length * 68 + 20));
  const spaceBelow = window.innerHeight - rect.bottom - viewportPadding;
  const spaceAbove = rect.top - viewportPadding;
  const placeAbove = spaceBelow < estimatedHeight && spaceAbove > spaceBelow;
  const left = Math.min(
    Math.max(viewportPadding, rect.left),
    Math.max(viewportPadding, window.innerWidth - width - viewportPadding),
  );
  const unclampedTop = placeAbove ? rect.top - estimatedHeight - gap : rect.bottom + gap;
  const top = Math.min(
    Math.max(viewportPadding, unclampedTop),
    Math.max(viewportPadding, window.innerHeight - estimatedHeight - viewportPadding),
  );

  menuDirection.value = placeAbove ? "above" : "below";
  menuStyle.value = {
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
  };
}

function scrollHighlightedOptionIntoView() {
  const option = listRef.value?.querySelector<HTMLElement>(`[data-index="${highlightedIndex.value}"]`);
  option?.scrollIntoView({
    block: "nearest",
  });
}

async function openMenu() {
  if (props.disabled || !props.options.length) {
    return;
  }

  syncHighlightedIndex();
  open.value = true;
  await nextTick();
  updateMenuPosition();
  listRef.value?.focus();
  scrollHighlightedOptionIntoView();
}

function toggleOpen() {
  if (open.value) {
    closeMenu();
    return;
  }

  void openMenu();
}

function selectOption(value: string) {
  model.value = value;
  closeMenu();
  triggerRef.value?.focus();
}

function moveHighlight(step: number) {
  if (!props.options.length) {
    return;
  }

  const optionCount = props.options.length;
  highlightedIndex.value = (highlightedIndex.value + step + optionCount) % optionCount;
}

function handleTriggerKeydown(event: KeyboardEvent) {
  if (event.key === "ArrowDown" || event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    void openMenu();
  }
}

function handleListKeydown(event: KeyboardEvent) {
  if (event.key === "Escape") {
    event.preventDefault();
    closeMenu();
    triggerRef.value?.focus();
    return;
  }

  if (event.key === "Tab") {
    closeMenu();
    return;
  }

  if (event.key === "ArrowDown") {
    event.preventDefault();
    moveHighlight(1);
    return;
  }

  if (event.key === "ArrowUp") {
    event.preventDefault();
    moveHighlight(-1);
    return;
  }

  if (event.key === "Home") {
    event.preventDefault();
    highlightedIndex.value = 0;
    return;
  }

  if (event.key === "End") {
    event.preventDefault();
    highlightedIndex.value = Math.max(0, props.options.length - 1);
    return;
  }

  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    const option = props.options[highlightedIndex.value];
    if (option) {
      selectOption(option.value);
    }
  }
}

function handlePointerDown(event: PointerEvent) {
  if (!open.value) {
    return;
  }

  const target = event.target;
  if (!(target instanceof Node)) {
    return;
  }

  const insideTrigger = rootRef.value?.contains(target);
  const insideMenu = menuShellRef.value?.contains(target);
  if (!insideTrigger && !insideMenu) {
    closeMenu();
  }
}

function handleViewportChange() {
  if (!open.value) {
    return;
  }

  updateMenuPosition();
}

watch(
  () => model.value,
  () => {
    syncHighlightedIndex();
  },
  { immediate: true },
);

watch([open, highlightedIndex], async ([isOpen]) => {
  if (!isOpen) {
    return;
  }

  await nextTick();
  updateMenuPosition();
  scrollHighlightedOptionIntoView();
});

onMounted(() => {
  document.addEventListener("pointerdown", handlePointerDown);
  window.addEventListener("resize", handleViewportChange);
  window.addEventListener("scroll", handleViewportChange, true);
});

onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", handlePointerDown);
  window.removeEventListener("resize", handleViewportChange);
  window.removeEventListener("scroll", handleViewportChange, true);
});
</script>
