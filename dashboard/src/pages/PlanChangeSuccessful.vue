<template>
	<div class="text-center text-center flex flex-col">
		<GreenCheckIcon class="mx-auto h-10 w-10 mb-4" />
		<span class="text-2xl font-semibold mb-2"> Plan modifié avec succès </span>
		<span class="text-base">
			Le plan de votre site a été changé de
			<span class="font-semibold">{{ currentPlan }}</span> à
			<span class="font-semibold">{{ selectedPlan }}</span>
		</span>
	</div>
</template>

<script>
export default {
	name: 'PlanChangeSuccessful',
	props: ['currentPlan', 'selectedPlan', 'step'],
	emits: ['update:step'],
};
</script>
