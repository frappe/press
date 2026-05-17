<script setup lang="ts">
import { ref } from 'vue'

interface Props {
	headerCss?: string
}

defineProps<Props>()

const opened = ref(false)
</script>

<template>
	<details :open="opened" @click="opened = !opened" class='cursor-pointer'>
		<summary class="flex items-center gap-2" :class="headerCss">
			<slot name="header" />
			<LucideChevronRight
				class="shrink-0 size-4 ml-auto transition-transform duration-300"
				:class='opened? "rotate-90":""'
			/>
		</summary>
	</details>

	<div
		:inert="!opened"
		class="grid transition-[grid-template-rows] duration-500"
		:class='opened? "grid-rows-[1fr]":"grid-rows-[0fr]"'
	>
		<div class="overflow-hidden"><slot /> </div>
	</div>
</template>
