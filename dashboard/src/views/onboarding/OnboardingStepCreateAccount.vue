<template>
	<div>
		<div class="flex">
			<GreenCheckIcon class="h-5 w-5" />
			<div class="ml-2 text-lg font-medium">Create account</div>
		</div>
		<div class="relative mt-1 pb-6 pl-7 text-sm text-gray-600">
			<p>
				Your account
				<span class="font-semibold">{{ $account.team.name }}</span> has been
				created.
			</p>

			<div
				style="width: 1px; height: 95%"
				class="absolute top-0 left-2.5 border-r border-gray-300"
			></div>
		</div>
	</div>
</template>
<script>
export default {
	name: 'OnboardingStepCreateAccount'
};
</script>
