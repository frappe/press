<template>
	<WizardCard v-if="options">
		<div class="mb-6 text-center">
			<h1 class="text-2xl font-bold">Create a new server</h1>
		</div>
	</WizardCard>
</template>

<script>
import WizardCard from '@/components/WizardCard.vue';
export default {
	name: 'NewServer',
	components: {
		WizardCard,
	},
	data() {
		return {
		};
	},
	async mounted() {
	},
	computed: {},
};
</script>
