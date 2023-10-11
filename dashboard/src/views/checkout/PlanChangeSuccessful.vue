<template>
	<div class="text-center text-center flex flex-col">
		<GreenCheckIcon class="mx-auto h-10 w-10 mb-4" />
		<span class="text-2xl font-semibold mb-2"> Plan Changed Successfully </span>
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
