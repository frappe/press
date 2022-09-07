<template>
	<div>
		<div class="flex">
			<GreenCheckIcon class="h-5 w-5" v-if="done" />
			<div v-else class="rounded-full bg-white">
				<FeatherIcon
					name="plus-circle"
					class="h-5 w-5 text-current text-gray-700"
				/>
			</div>
			<div class="ml-2 text-lg font-medium">Select a plan for your site</div>
		</div>
		<div class="pl-7">
			<div class="mt-1 text-sm text-gray-600">
				Select a plan for your site and it will be applied after your trial
				ends.
			</div>
			<Button
				v-if="active && !done && $account.onboarding.erpnext_site"
				class="mt-2"
				:route="`/sites/${$account.onboarding.erpnext_site.name}`"
			>
				Select a plan
			</Button>
		</div>
	</div>
</template>
<script>
export default {
	name: 'OnboardingStepSelectSitePlan',
	props: ['active', 'done']
};
</script>
