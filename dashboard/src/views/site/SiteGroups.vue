<template>
	<div>
		<div class="flex">
			<div class="flex w-full px-3 py-4">
				<div class="w-4/12 text-base font-medium text-gray-900">Site Name</div>
				<div class="w-2/12 text-base font-medium text-gray-900">Status</div>
				<div class="w-2/12 text-base font-medium text-gray-900">Region</div>
				<div class="w-2/12 text-base font-medium text-gray-900">Tags</div>
				<div class="w-2/12 text-base font-medium text-gray-900">Plan</div>
			</div>
			<div class="w-8" />
		</div>
		<ListView :items="groupedSites" :dropdownItems="dropdownItems" />
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
import ListView from '@/components/ListView.vue';

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
		SiteList,
		ListView
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
		},
		siteBadge(site) {
			let status = site.status;
			if (site.update_available && site.status == 'Active') {
				status = 'Update Available';
			}

			let usage = Math.max(
				site.current_cpu_usage,
				site.current_database_usage,
				site.current_disk_usage
			);
			if (usage && usage >= 80 && status == 'Active') {
				status = 'Attention Required';
			}
			if (site.trial_end_date) {
				status = 'Trial';
			}
			return status;
		}
	},
	computed: {
		groupedSites() {
			return this.sites.reduce((acc, curr) => {
				const { title, version } = curr;
				const newCurr = {
					name: curr.host_name || curr.name,
					status: this.siteBadge(curr),
					server_region_info: curr.server_region_info,
					link: { name: 'SiteOverview', params: { siteName: curr.name } },
					tags: curr.tags,
					plan: curr.plan
				};

				const existingGroup = acc.find(group => group.group === title);

				if (existingGroup) existingGroup.items.push(newCurr);
				else acc.push({ group: title, version, items: [newCurr] });

				return acc;
			}, []);
		}
	}
};
</script>
