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
			<div class="ml-2 text-lg font-medium">Create site</div>
		</div>
		<div class="pl-7">
			<div class="mt-1 text-sm text-gray-600">
				Creating a new site is as easy as choosing a subdomain and a plan.
			</div>
			<Button v-if="active && !done" class="mt-2" route="/sites/new"
				>Create</Button
			>
		</div>
	</div>
</template>
<script>
export default {
	name: 'OnboardingStepCreateAccount',
	props: ['active', 'done']
};
</script>
