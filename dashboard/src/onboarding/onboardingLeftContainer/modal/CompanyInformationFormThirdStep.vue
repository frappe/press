<script setup>
const emit = defineEmits(['continue']);

function tryContinue() {
	emit('continue');
}

defineExpose({ tryContinue });
</script>

<template>
	<div class="flex min-h-[200px] flex-col gap-3 py-1">
		<p class="text-p-base text-ink-gray-6">
			Step 3 — Add your final step here (e.g. review and submit).
		</p>
	</div>
</template>
