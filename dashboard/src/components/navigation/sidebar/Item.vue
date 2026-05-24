<script setup lang="ts">
import type { NavItemProps } from "./types";
import { inject } from "vue";

const collapsed = inject("collapsed");
const collapsedCss = inject("collapsedCss");

const props = withDefaults(defineProps<NavItemProps>(), {
  is: "router-link",
});
</script>

<template>
  <component :to="route" :is @click='onClick'
    class="flex text-left items-center rounded w-full py-1.5 px-2 text-ink-gray-7 transition" :class="[
      isActive
        ? 'bg-surface-gray-2 md:bg-surface-white dark:bg-surface-gray-2 text-ink-gray-8 md:shadow-sm'
        : 'hover:bg-surface-gray-2',
      disabled ? 'pointer-events-none opacity-50' : '',
      collapsed ? 'md:w-fit gap-2 md:gap-0' : 'gap-2 md:w-full',
    ]">
    <slot name='prefix'>
      <component :is="prefix || icon" class="shrink-0 size-4 text-ink-gray-6" :class="isActive ? 'text-ink-gray-8' : ''" />
    </slot>

    <span class="text-sm flex-1" :class='collapsedCss' >{{ name }}</span>
    <slot name="suffix">
      <span v-if='suffix' :class='collapsedCss'  class='text-xs'>{{ suffix}} </span>
    </slot>
  </component>
</template>
