<script setup lang="ts">
import type { NavItemProps } from "./types";

const props = withDefaults(defineProps<NavItemProps>(), {
	is: "router-link",
});
</script>

<template>
  <component :to="route" :is
    class="flex text-left items-center rounded px-2 py-1.5 text-ink-gray-7 transition gap-2 w-full" :class="[
      isActive
        ? 'bg-surface-gray-2 md:bg-surface-white dark:bg-surface-gray-2 text-ink-gray-8 md:shadow-sm'
        : 'hover:bg-surface-gray-2',
      disabled ? 'pointer-events-none opacity-50' : '',
    ]">
    <slot name='prefix'>
      <component :is="icon" class="size-4 text-ink-gray-6" :class="isActive ? 'text-ink-gray-8' : ''" />
    </slot>

    <span class="text-sm flex-1 collapsed">{{ name }}</span>
    <slot name="suffix" />
  </component>
</template>
