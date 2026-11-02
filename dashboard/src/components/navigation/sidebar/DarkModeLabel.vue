<script setup lang="ts">
import { Badge } from 'frappe-ui';
import LucideMoon from '~icons/lucide/moon';
</script>

<template>
  <div class='flex items-center gap-2 w-full text-ink-gray-7'>
    <LucideMoon class='size-4 text-ink-gray-6' />
    <span>Dark Mode</span>
    <Badge label="beta" heme="orange" class="ml-auto" />
  </div>
</template>
