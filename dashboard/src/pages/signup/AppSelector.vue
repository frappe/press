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
			subtitle="Select the app you want to install on your site."
		>
			<div v-if="$resources.availableApps.loading">
				<div class="flex h-40 justify-center">
					<LoadingText />
				</div>
			</div>
			<div v-else>
				<div
					class="flex h-full max-h-96 flex-col items-center space-y-2 overflow-auto py-2"
				>
					<div
						v-for="app in $resources.availableApps.data"
						:key="app.name"
						class="w-full"
					>
						<div
							class="flex cursor-pointer items-center rounded border border-gray-100 p-2"
							:class="{
								'bg-gray-100': selectedApp?.name === app.name,
								'border-gray-100 hover:bg-gray-50':
									selectedApp?.name !== app.name,
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
								<p class="line-clamp-1 text-sm text-gray-600">
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
			</div>
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
	mounted() {
		this.email = localStorage.getItem('login_email');
		if (window.posthog?.__loaded) {
			window.posthog.identify(this.email || window.posthog.get_distinct_id(), {
				app: 'frappe_cloud',
				action: 'login_signup'
			});

			window.posthog.startSessionRecording();
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
