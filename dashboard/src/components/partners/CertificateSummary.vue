<template>
	<div>
		<Dialog
			v-model="show"
			:options="{ title: 'Evaluation Summary', size: 'xl' }"
		>
			<template #body-content>
				<div :class="`bg-${color}-50 p-4 rounded-lg`">
					<p :class="`text-p-base text-${color}-800`">
						{{ summary }}
					</p>
				</div>
			</template>
		</Dialog>
	</div>
</template>
<script setup>
const show = defineModel();
const props = defineProps({
	summary: {
		type: String,
		default: '',
	},
	color: {
		type: String,
		default: 'blue',
	},
});
</script>
