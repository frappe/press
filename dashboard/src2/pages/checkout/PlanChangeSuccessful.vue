<template>
	<div class="flex flex-col text-center">
		<GreenCheckIcon class="mx-auto mb-4 h-10 w-10" />
		<span class="mb-2 text-2xl font-semibold"> Plan Changed Successfully </span>
		<span class="text-base">
			Your site plan has been changed from
			<span class="font-semibold">{{ currentPlan }}</span> to
			<span class="font-semibold">{{ selectedPlan }}</span>
		</span>
	</div>
</template>

<script>
export default {
	name: 'PlanChangeSuccessful',
	props: ['currentPlan', 'selectedPlan', 'step'],
	emits: ['update:step']
};
</script>
