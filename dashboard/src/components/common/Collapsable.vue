<script setup lang="ts">
import { ref } from 'vue'

interface Props {
	headerCss?: string
	disabled?: boolean
}

const props = defineProps<Props>()

const opened = ref(false)

function toggle() {
	if (props.disabled) return
	opened.value = !opened.value
}
</script>

<template>
	<details
		:open="opened"
		:class='disabled? "opacity-60 cursor-not-allowed":"cursor-pointer"'
	>
		<summary
			class="flex items-center gap-2"
			:class="headerCss"
			@click.prevent="toggle"
		>
			<slot name="header" />
			<LucideChevronUp
				class="shrink-0 size-4 ml-auto transition-transform duration-300"
				:class='opened? "":"rotate-180"'
			/>
		</summary>
	</details>

	<div
		:inert="!opened"
		class="grid duration-500"
		:class='opened? "grid-rows-[1fr]":"grid-rows-[0fr]"'
	>
		<div class="overflow-hidden"><slot /> </div>
	</div>
</template>
