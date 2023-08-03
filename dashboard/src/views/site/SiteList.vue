<template>
	<div class="space-y-8">
		<div v-for="groupedSite in groupedSites" :key="groupedSite.releaseGroup">
			<h3 class="mb-3 text-base font-semibold text-gray-800">
				{{ groupedSite.releaseGroup }}
			</h3>
			<div class="grid grid-cols-4 gap-4">
				<SiteCard
					v-for="site in groupedSite.sites"
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
			<Input
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
	name: 'SiteList',
	props: {
		sites: {
			default: []
		},
		showBenchInfo: {
			default: true
		}
	},
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
	},
	computed: {
		groupedSites() {
			return this.sites.reduce((acc, curr) => {
				const { title } = curr;
				const existingGroup = acc.find(group => group.releaseGroup === title);

				if (existingGroup) existingGroup.sites.push(curr);
				else acc.push({ releaseGroup: title, sites: [curr] });

				return acc;
			}, []);
		}
	}
};
</script>
