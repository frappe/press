<script setup lang="ts">
interface Props {
  headerCss?: string
}

defineProps<Props>();
</script>

<template>
  <div>
    <details class="group peer">
      <summary class='flex items-center gap-3' :class="headerCss">
        <slot name='header' />
        <LucideChevronRight class="size-4 ml-auto transition-transform duration-200 group-open:rotate-90" />
      </summary>
    </details>

    <div class="grid grid-rows-[0fr] transition-[grid-template-rows] duration-300 peer-open:grid-rows-[1fr]">
      <div class="overflow-hidden flex flex-col gap-1 ml-5">
        <slot />
      </div>
    </div>
  </div>
</template>
