<template>
	<div v-if="error" class="mx-auto text-center w-fit">
		<p class="text-sm font-medium">
			{{ errorMessage }}
		</p>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
	doctype: string;
	docname: string;
	error?: Error;
}>();

const isPermissionError = computed(() => {
	return props.error?.message.endsWith('PermissionError');
});

const errorMessage = computed(() => {
	if (isPermissionError.value) {
		return 'Vous n\'avez pas la permission de voir cette ressource';
	} else {
		return props.error?.message || 'Une erreur inattendue est survenue';
	}
});
</script>
