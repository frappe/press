<template>
	<div
		class="sm:rounded-md sm:border sm:border-gray-100 sm:py-1 sm:px-2 sm:shadow"
	>
		<div
			class="py-2 text-base text-gray-600 sm:px-2"
			v-if="sites && sites.length === 0"
		>
			No sites
		</div>
		<div class="py-2" v-for="(site, index) in sites" :key="site.name">
			<div class="flex items-center justify-between">
				<router-link
					:to="`/sites/${site.name}/overview`"
					class="block w-full rounded-md py-2 hover:bg-gray-50 sm:px-2"
				>
					<div class="flex items-center justify-between">
						<div
							class="hover:text-ellipses truncate break-all text-base w-1/2 sm:w-4/12"
						>
							{{ site.host_name || site.name }}
						</div>
						<div class="text-base w-1/3 sm:w-3/12">
							<Badge
								class="pointer-events-none"
								:colorMap="$badgeStatusColorMap"
								:label="siteBadge(site)"
							/>
						</div>
						<div
							v-if="showBenchInfo"
							class="text-base sm:w-4/12 hidden sm:block"
						>
							<div class="hover:text-ellipses truncate break-all hover:w-full">
								{{ site.title }}
							</div>
						</div>
						<div
							v-if="showBenchInfo"
							class="text-base hidden sm:block sm:w-3/12"
						>
							<Badge>
								{{ site.version }}
							</Badge>
						</div>
						<div class="hidden w-1/12 text-sm text-gray-600 sm:block">
							{{ $dayjs.shortFormating($dayjs(site.creation).fromNow()) }}
						</div>
					</div>
				</router-link>

				<div class="text-right text-base">
					<Dropdown
						v-if="site.status === 'Active' || site.status === 'Updating'"
						:options="dropdownItems(site)"
					>
						<template v-slot="{ open }">
							<Button icon="more-horizontal" />
						</template>
					</Dropdown>
					<div v-else class="h-[30px] w-[30px]"></div>
				</div>
			</div>
			<div
				class="translate-y-2 transform"
				:class="{ 'border-b': index < sites.length - 1 }"
			/>
		</div>

		<Dialog
			:options="{ title: 'Login As Administrator' }"
			v-model="showReasonForAdminLoginDialog"
		>
			<template v-slot:body-content>
				<Input
					label="Reason for logging in as Administrator"
					type="textarea"
					v-model="reasonForAdminLogin"
					required
				/>

				<ErrorMessage class="mt-3" :message="errorMessage" />
			</template>

			<template #actions>
				<Button
					:loading="adminLoginInProcess"
					@click="proceedWithLoginAsAdmin"
					appearance="primary"
					>Proceed</Button
				>
			</template>
		</Dialog>
	</div>
</template>
<script>
import { loginAsAdmin } from '@/controllers/loginAsAdmin';

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
	data() {
		return {
			adminLoginInProcess: false,
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
		},
		dropdownItems(site) {
			return [
				{
					label: 'Visit Site',
					handler: () => {
						window.open(`https://${site.name}`, '_blank');
					}
				},
				{
					label: 'Login As Admin',
					handler: () => {
						if (this.$account.team.name == site.team) {
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
