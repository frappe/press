<template>
	<div class="relative h-full">
		<div class="relative z-10 mx-auto pt-8 sm:pt-16">
			<!-- logo -->
			<div
				class="flex flex-col items-center"
				@dblclick="redirectForFrappeioAuth"
			>
				<FCLogo class="inline-block h-12 w-12" />
			</div>
			<!-- card -->
			<div
				class="mx-auto w-full bg-white px-4 py-8 sm:mt-6 sm:w-3/6 sm:rounded-2xl sm:px-6 sm:py-6 sm:shadow-2xl"
			>
				<!-- title -->
				<div class="mb-7.5 text-center">
					<p
						class="text-center text-lg font-medium leading-5 tracking-tight text-gray-900"
					>
						Choose an app below to create your first site.
					</p>
				</div>
				<div
					v-if="$resources.availableApps.loading"
					class="flex justify-center"
				>
					<LoadingText />
				</div>
				<OnboardingAppSelector v-else :apps="$resources.availableApps.data" />
			</div>
		</div>
		<div class="flex w-full">
			<Button
				class="mx-auto mt-4"
				label="Skip to Dashboard"
				variant="ghost"
				icon-right="arrow-right"
				:route="{ name: 'Site List' }"
			/>
		</div>
	</div>
</template>
<script>
import OnboardingAppSelector from './OnboardingAppSelector.vue';

export default {
	name: 'Onboarding',
	components: {
		OnboardingAppSelector,
	},
	resources: {
		availableApps() {
			return {
				url: 'press.api.marketplace.get_marketplace_apps_for_onboarding',
				auto: true,
			};
		},
	},
	methods: {
		redirectForFrappeioAuth() {
			window.location = '/f-login';
		},
	},
};
</script>
