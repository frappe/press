<script setup lang="ts">
import LucideChevronRight from "~icons/lucide/chevron-right";
import Item from "./Item.vue";
import type { NavItemProps } from "./types";
import { inject } from "vue";

const collapsed = inject("collapsed");
const collapsedCss = inject("collapsedCss");

interface Props extends NavItemProps {
  children: NavItemProps[];
}

defineProps<Props>();
</script>

<template>
  <details class="group peer" :open='isActive'>
    <Item is="summary" :icon :name>
      <template #suffix>
        <LucideChevronRight :class='collapsedCss' class="text-ink-gray-4 size-4 transition-transform duration-200 group-open:rotate-90" />
      </template>
    </Item>
  </details>

  <div class="grid grid-rows-[0fr] transition-[grid-template-rows] duration-300 peer-open:grid-rows-[1fr]">
    <div class="overflow-hidden flex flex-col gap-1" :class="collapsed ? '' : 'ml-5'">
      <Item v-for="(subItem, i) in children" :key="subItem.name" v-bind="subItem"
        :class="{ 'mb-1': i == children.length - 1 }" />
    </div>
  </div>
</template>
