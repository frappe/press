<script setup lang="ts">
import { ref } from 'vue'

interface Props {
	headerCss?: string
<<<<<<< HEAD
<<<<<<< HEAD
	disabled?: boolean
}

const props = defineProps<Props>()
<<<<<<< HEAD

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
=======
=======
	disabled?: boolean
>>>>>>> b3ef93793 (feat(Collapsible): add disabled prop)
}

const props =defineProps<Props>()
=======
>>>>>>> b5f34e325 (fix(collapsable): add @click.prevent)

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
<<<<<<< HEAD
		<summary class="flex items-center gap-2" :class="headerCss">
>>>>>>> 7fb5b9f2f (feat(component): Collapsible)
=======
		<summary
			class="flex items-center gap-2"
			:class="headerCss"
			@click.prevent="toggle"
		>
>>>>>>> b5f34e325 (fix(collapsable): add @click.prevent)
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
