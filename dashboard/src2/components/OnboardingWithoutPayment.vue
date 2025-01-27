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
					<p class="mb-2 text-2xl font-semibold leading-6 text-gray-900">
						Welcome to Frappe Cloud
					</p>
					<p
						class="break-words text-base font-normal leading-[21px] text-gray-700"
					>
						Choose an app below to create your first site.
					</p>
				</div>
				<OnboardingAppSelector :apps="$resources.availableApps.data" />
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
import ObjectList from './ObjectList.vue';
import OnboardingAppSelector from './OnboardingAppSelector.vue';
import SaaSLoginBox from './auth/SaaSLoginBox.vue';

export default {
	name: 'Onboarding',
	components: {
		ObjectList,
		SaaSLoginBox,
		OnboardingAppSelector,
	},
	mounted() {
		if (window.posthog?.__loaded) {
			window.posthog.identify(this.$team.doc.user, {
				app: 'frappe_cloud',
				action: 'onboarding',
			});
			window.posthog.startSessionRecording();
		}
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
