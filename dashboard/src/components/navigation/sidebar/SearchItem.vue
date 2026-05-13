<script setup lang="ts">
import { searchModalOpen } from "@/data/ui";
import { isMac } from "@/utils/device";
import LucideSearch from "~icons/lucide/search";
import Item from "./Item.vue";
</script>

<template>
  <Item is='BUTTON' name='Search' :icon='LucideSearch' @click="() => (searchModalOpen = true)">
    <template #suffix>
      <span class="inline-flex items-center text-sm gap-1">
        {{ isMac() ? '⌘ K' : 'Ctrl+k' }}
      </span>
    </template>
  </Item>
</template>
