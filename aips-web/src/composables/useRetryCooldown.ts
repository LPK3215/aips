import { computed, onBeforeUnmount, ref } from "vue";


export function useRetryCooldown() {
  const secondsRemaining = ref(0);
  let timer: number | null = null;

  function clearCooldown() {
    if (timer !== null) {
      window.clearInterval(timer);
      timer = null;
    }
    secondsRemaining.value = 0;
  }

  function startCooldown(seconds: number | null | undefined) {
    if (!seconds || seconds <= 0) {
      return;
    }

    clearCooldown();
    secondsRemaining.value = Math.ceil(seconds);
    timer = window.setInterval(() => {
      secondsRemaining.value -= 1;
      if (secondsRemaining.value <= 0) {
        clearCooldown();
      }
    }, 1000);
  }

  onBeforeUnmount(() => {
    clearCooldown();
  });

  return {
    secondsRemaining,
    isCoolingDown: computed(() => secondsRemaining.value > 0),
    startCooldown,
    clearCooldown,
  };
}
