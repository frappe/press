<template>
	<div>
		<div class="flex">
			<div class="flex w-full px-3 py-4">
				<div class="w-4/12 text-base font-medium text-gray-900">Site Name</div>
				<div class="w-2/12 text-base font-medium text-gray-900">Status</div>
				<div class="w-2/12 text-base font-medium text-gray-900">Region</div>
				<div class="w-2/12 text-base font-medium text-gray-900">Plan</div>
			</div>
			<div class="w-8" />
		</div>
		<div v-for="groupedSite in groupedSites" :key="groupedSite.releaseGroup">
			<div class="flex space-x-2 rounded-sm bg-gray-50 px-3 py-1.5">
				<h3 class="text-base font-medium text-gray-800">
					{{ groupedSite.releaseGroup }}
				</h3>
				<div class="text-sm text-gray-600">
					{{ groupedSite.sites[0].version }}
				</div>
			</div>
			<div v-for="(site, i) in groupedSite.sites" class="flex flex-col">
				<SiteList
					:key="site.name"
					:site="site"
					:dropdownItems="dropdownItems"
				/>
				<div v-if="i < groupedSite.sites.length - 1" class="mx-2.5 border-b" />
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
import SiteList from './SiteList.vue';

export default {
	name: 'SiteGroups',
	props: {
		sites: {
			default: []
		},
		showBenchInfo: {
			default: true
		}
	},
	components: {
		SiteList
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
					},
					condition: () =>
						site.status === 'Active' || site.status === 'Updating'
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
					},
					condition: () =>
						site.status === 'Active' || site.status === 'Updating'
				},
				{
					label: 'Manage Bench',
					onClick: () => {
						this.$router.push({
							name: 'Bench',
							params: { benchName: site.group }
						});
					},
					condition: () => true
				}
			].filter(item => item.condition());
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
