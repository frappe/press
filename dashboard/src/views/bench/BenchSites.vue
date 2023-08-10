<template>
	<div class="space-y-8">
		<div v-for="bench in $resources.benchesWithSites.data" :key="bench.bench">
			<h3 class="mb-1.5 text-base font-semibold text-gray-800">
				{{ bench.bench }}
			</h3>
			<div class="mb-5 text-sm text-gray-500">
				Deployed on
				{{ formatDate(bench.deployed_on, 'DATETIME_SHORT', true) }}
			</div>
			<div class="grid grid-cols-4 gap-4">
				<SiteCard
					v-for="site in bench.sites"
					:key="site.name"
					:site="site"
					:dropdownItems="dropdownItems"
				/>
			</div>
		</div>
	</div>

	<Dialog
		:options="{
			title: 'Login As Administrator',
			actions: [
				{
					label: 'Proceed',
					variant: 'solid',
					onClick: proceedWithLoginAsAdmin
				}
			]
		}"
		v-model="showReasonForAdminLoginDialog"
	>
		<template #body-content>
			<FormControl
				label="Reason for logging in as Administrator"
				type="textarea"
				v-model="reasonForAdminLogin"
				required
			/>
			<ErrorMessage class="mt-3" :message="errorMessage" />
		</template>
	</Dialog>
</template>
<script>
import { loginAsAdmin } from '@/controllers/loginAsAdmin';
import SiteCard from '@/components/SiteCard.vue';

export default {
	name: 'SitesList',
	props: ['bench'],
	components: {
		SiteCard
	},
	data() {
		return {
			reasonForAdminLogin: '',
			errorMessage: null,
			showReasonForAdminLoginDialog: false,
			siteForLogin: null
		};
	},
	resources: {
		benchesWithSites() {
			return {
				method: 'press.api.bench.benches_with_sites',
				params: {
					name: this.bench?.name
				},
				auto: true
			};
		},
		loginAsAdmin() {
			return loginAsAdmin('placeholderSite'); // So that RM does not yell at first load
		}
	},
	methods: {
		dropdownItems(site) {
			return [
				{
					label: 'Visit Site',
					onClick: () => {
						window.open(`https://${site.name}`, '_blank');
					}
				},
				{
					label: 'Login As Admin',
					onClick: () => {
						if (this.$account.team.name === site.team) {
							return this.$resources.loginAsAdmin.submit({
								name: site.name
							});
						}

						this.siteForLogin = site.name;
						this.showReasonForAdminLoginDialog = true;
					}
				}
			];
		},
		proceedWithLoginAsAdmin() {
			this.errorMessage = '';

			if (!this.reasonForAdminLogin.trim()) {
				this.errorMessage = 'Reason is required';
				return;
			}

			this.$resources.loginAsAdmin.submit({
				name: this.siteForLogin,
				reason: this.reasonForAdminLogin
			});

			this.showReasonForAdminLoginDialog = false;
		}
	}
};
</script>
