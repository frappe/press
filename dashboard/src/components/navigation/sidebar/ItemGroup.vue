<script setup lang="ts">
import LucideChevronRight from "~icons/lucide/chevron-right";
import Item from "./Item.vue";
import type { NavItemProps } from "./types";

interface Props extends NavItemProps {
  children: NavItemProps[];
}

defineProps<Props>();
</script>

<template>
  <details class="group peer" :open='isActive'>
    <Item is="summary" :icon :name>
      <template #suffix>
        <LucideChevronRight class="text-ink-gray-4 size-4 transition-transform duration-200 group-open:rotate-90" />
      </template>
    </Item>
  </details>

  <div class="grid grid-rows-[0fr] transition-[grid-template-rows] duration-300 peer-open:grid-rows-[1fr]">
    <div class="overflow-hidden flex flex-col gap-1 ml-5">
      <Item v-for="(subItem, i) in children" :key="subItem.name" v-bind="subItem"
        :class="{ 'mb-1': i == children.length - 1 }" />
    </div>
  </div>
</template>
