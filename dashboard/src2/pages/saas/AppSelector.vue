<template>
	<div
		class="px-5 py-10"
		v-if="$team?.doc"
		:class="{
			'h-max min-h-full ':
				!$team.doc.onboarding.is_saas_user &&
				!$team.doc.onboarding.site_created,
		}"
	>
		<LoginBox
			title="Select an app to get started"
			subtitle="Select the app you need to configure them effortlessly"
		>
			<!-- app list with set height -->
			<div
				class="flex h-full max-h-96 flex-col items-center justify-center space-y-2 overflow-auto py-2"
			>
				<div
					v-for="app in $resources.availableApps.data"
					:key="app.name"
					class="w-full"
				>
					<div
						class="flex cursor-pointer items-center rounded border border-gray-100 p-2 hover:bg-gray-50"
						:class="{
							'bg-gray-100': selectedApp?.name === app.name,
							'border-gray-100': selectedApp?.name !== app.name,
						}"
						@click="selectedApp = app"
					>
						<img
							:src="app.image"
							:alt="app.title"
							class="mr-2 h-8 w-8 rounded"
						/>
						<div class="space-y-1">
							<p class="text-lg font-medium">{{ app.title }}</p>
							<p class="line-clamp-1 text-sm text-gray-500">
								{{ app.description }}
							</p>
						</div>
					</div>
				</div>
			</div>
			<Button
				class="mt-4 w-full"
				:label="selectedApp ? `Install ${selectedApp.title}` : 'Install app'"
				variant="solid"
				:disabled="!selectedApp"
				@click="openInstallAppPage(selectedApp)"
			/>
			<template #footer>
				<span class="ml-4 text-base font-normal text-gray-600">
					{{ 'Skip creating a site? ' }}
				</span>
				<router-link
					class="text-base font-normal text-gray-900 underline hover:text-gray-700"
					:to="{
						name: 'Site List',
					}"
				>
					Go to Dashboard
				</router-link>
			</template>
		</LoginBox>

		<!-- <div class="relative h-full">
			<div class="relative z-10 mx-auto pt-8 sm:pt-16">
				<div
					class="flex flex-col items-center"
					@dblclick="redirectForFrappeioAuth"
				>
					<FCLogo class="inline-block h-12 w-12" />
				</div>
				<div
					class="mx-auto w-full bg-white px-4 py-8 sm:mt-6 sm:w-3/6 sm:rounded-2xl sm:px-6 sm:py-6 sm:shadow-2xl"
				>
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
		</div> -->
	</div>
</template>
<script>
import { getTeam } from '../../data/team';
import OnboardingAppSelector from './../../components/OnboardingAppSelector.vue';
import LoginBox from './../../components/auth/LoginBox.vue';

export default {
	name: 'Welcome',
	components: {
		OnboardingAppSelector,
		LoginBox,
	},
	data() {
		return {
			selectedApp: null,
		};
	},
	resources: {
		availableApps() {
			return {
				url: 'press.api.marketplace.get_marketplace_apps_for_onboarding',
				auto: true,
			};
		},
		getAccountRequestForProductSignup() {
			return {
				url: 'press.api.product_trial.get_account_request_for_product_signup',
			};
		},
	},
	beforeRouteEnter(to, from, next) {
		let $team = getTeam();
		window.$team = $team;
		if ($team.doc.onboarding.complete && $team.doc.onboarding.site_created) {
			next({ name: 'Site List' });
		} else if (to.query.is_redirect && $team.doc.onboarding.site_created) {
			next({ name: 'Site List' });
		} else {
			next();
		}
	},
	methods: {
		openInstallAppPage(app) {
			this.$resources.getAccountRequestForProductSignup
				.submit()
				.then((account_request) =>
					this.$router.push({
						name: 'SignupSetup',
						params: { productId: app.name },
						query: {
							account_request: account_request,
						},
					}),
				);
		},
	},
};
</script>
