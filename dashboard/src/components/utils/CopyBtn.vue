<script setup lang="ts">
import { ref } from 'vue';

interface Props {
	text: string;
}

const props = defineProps<Props>();

const copied = ref(false);

const copy = () => {
	const clipboard = navigator.clipboard;

	clipboard.writeText(props.text).then(() => {
		copied.value = true;
		setTimeout(() => {
			copied.value = false;
		}, 1000);
	});
};
</script>

<template>
	<button @click="copy">
		<lucide-clipboard
			v-if="!copied"
			class="size-3.5"
			:class="{ 'fade-in': !copied }"
		/>
		<lucide-circle-check v-else class="size-3.5 animate-in fade-in" />
	</button>
</template>

<style scoped>
.fade-in {
	animation: fadeIn 0.4s ease-in-out;
}

@keyframes fadeIn {
	from {
		opacity: 0;
	}
	to {
		opacity: 1;
	}
}
</style>
