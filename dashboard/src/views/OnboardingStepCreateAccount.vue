<template>
	<div>
		<div class="flex">
			<GreenCheckIcon class="w-5 h-5" />
			<div class="ml-2 text-lg font-medium">
				Create account
			</div>
		</div>
		<div class="relative pb-6 mt-1 text-sm text-gray-600 pl-7">
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
