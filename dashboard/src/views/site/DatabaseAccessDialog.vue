<template>
	<Dialog
		:options="{ title: 'Access Database' }"
		v-if="site"
		:modelValue="Boolean(site) && show"
		@close="dialogClosed"
	>
		<template v-slot:body-content>
			<LoadingText v-if="$resources.fetchDatabaseAccessInfo.loading" />

			<!-- Not available on current plan, upsell higher plans -->
			<div v-else-if="!databaseAccessInfo?.is_available_on_current_plan">
				<div>
					<p class="text-base">
						Database access is not available on your current plan. Please
						upgrade your plan to access your site database.
					</p>

					<Button
						class="mt-4 w-full"
						variant="solid"
						@click="showChangePlanDialog = true"
						>Upgrade Site Plan</Button
					>
				</div>

				<Dialog
					:options="{
						title: 'Upgrade Plan',
						actions: [
							{
								label: 'Submit',
								variant: 'solid',
								loading: $resources.changePlan.loading,
								onClick: () => $resources.changePlan.submit()
							}
						]
					}"
					v-model="showChangePlanDialog"
				>
					<template v-slot:body-content>
						<SitePlansTable
							class="mt-3"
							:plans="plans"
							v-model:selectedPlan="selectedPlan"
						/>
						<ErrorMessage class="mt-4" :message="$resources.changePlan.error" />
					</template>
				</Dialog>
			</div>

			<!-- Available on the current plan -->
			<div v-else>
				<div v-if="databaseAccessInfo">
					<div v-if="databaseAccessInfo.is_database_access_enabled">
						<div>
							<p class="mb-2 text-base font-semibold text-gray-700">
								Using an Analytics or Business Intelligence Tool
							</p>
							<p class="mb-2 text-base">
								Use following credentials with your analytics or business
								intelligence tool
							</p>
							<p class="ml-1 font-mono text-sm">
								Host: {{ databaseAccessInfo.credentials.host }}
							</p>
							<p class="ml-1 font-mono text-sm">
								Port: {{ databaseAccessInfo.credentials.port }}
							</p>
							<p class="ml-1 font-mono text-sm">
								Database Name: {{ databaseAccessInfo.credentials.database }}
							</p>
							<p class="ml-1 font-mono text-sm">
								Username: {{ databaseAccessInfo.credentials.username }}
							</p>
							<p class="ml-1 font-mono text-sm">
								Password: {{ databaseAccessInfo.credentials.password }}
							</p>
						</div>
						<div class="pb-2 pt-5">
							<p class="mb-2 text-base font-semibold text-gray-700">
								Using MariaDB Client
							</p>
							<p class="mb-2 text-base">
								<span
									>Run this command in your terminal to access MariaDB
									console</span
								>
							</p>
							<ClickToCopyField class="ml-1" :textContent="dbAccessCommand" />
							<p class="mt-3 text-sm">
								Note: You should have a
								<span class="font-mono">mariadb</span> client installed on your
								computer.
							</p>
						</div>
					</div>
					<div v-else>
						<p class="mb-2 text-sm">
							Database console access is disabled for this site.
						</p>
					</div>
				</div>

				<ErrorMessage class="mt-3" :message="$resourceErrors || error" />

				<div class="mt-4">
					<div
						v-if="
							databaseAccessInfo &&
							!databaseAccessInfo.is_database_access_enabled
						"
						class="mb-2"
					>
						<!-- Enable Read-Write Access -->
						<input
							id="enable-read-write-access"
							type="checkbox"
							class="h-4 w-4 rounded border-gray-300 text-red-600 focus:ring-red-500"
							v-model="enableReadWriteAccess"
						/>
						<label for="skip-failing" class="ml-1 text-sm text-gray-900">
							Enable Read-Write Access
						</label>
						<ErrorMessage
							class="mt-2"
							:message="
								enableReadWriteAccess &&
								'Your credentials can be used to modify or wipe your database'
							"
						/>
					</div>
					<Button
						v-if="
							databaseAccessInfo &&
							!databaseAccessInfo.is_database_access_enabled
						"
						@click="$resources.enableDatabaseAccess.submit()"
						:loading="
							$resources.enableDatabaseAccess.loading || pollingAgentJob
						"
						variant="solid"
						class="w-full"
						>Enable
						{{ enableReadWriteAccess ? 'Read-Write' : 'Read-Only' }}
						Access</Button
					>

					<Button
						v-if="
							databaseAccessInfo &&
							databaseAccessInfo.is_database_access_enabled
						"
						@click="$resources.disableDatabaseAccess.submit()"
						:loading="
							$resources.disableDatabaseAccess.loading || pollingAgentJob
						"
						class="w-full"
						>Disable Access</Button
					>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script>
import ClickToCopyField from '@/components/ClickToCopyField.vue';
import SitePlansTable from '@/components/SitePlansTable.vue';
import { notify } from '@/utils/toast';

export default {
	props: ['site', 'show'],
	data() {
		return {
			pollingAgentJob: false,
			showChangePlanDialog: false,
			selectedPlan: null,
			enableReadWriteAccess: false,
			error: null
		};
	},
	components: {
		ClickToCopyField,
		SitePlansTable
	},
	resources: {
		fetchDatabaseAccessInfo() {
			return {
				url: 'press.api.site.get_database_access_info',
				params: {
					name: this.site
				},
				auto: true
			};
		},
		enableDatabaseAccess() {
			return {
				url: 'press.api.site.enable_database_access',
				params: {
					name: this.site,
					mode: this.enableReadWriteAccess ? 'read_write' : 'read_only'
				},
				onSuccess(d) {
					this.pollDatabaseAccessJob(d);
				}
			};
		},
		disableDatabaseAccess() {
			return {
				url: 'press.api.site.disable_database_access',
				params: {
					name: this.site
				},
				onSuccess(d) {
					this.pollDatabaseAccessJob(d);
				}
			};
		},
		plans() {
			return {
				url: 'press.api.site.get_plans',
				params: {
					name: this.site
				},
				initialData: [],
				auto: true
			};
		},
		changePlan() {
			return {
				url: 'press.api.site.change_plan',
				params: {
					name: this.site,
					plan: this.selectedPlan?.name
				},
				onSuccess() {
					notify({
						title: `Plan changed to ${this.selectedPlan.plan_title}`,
						icon: 'check',
						color: 'green'
					});
					this.showChangePlanDialog = false;
					this.selectedPlan = null;
					this.$resources.plans.reset();
					this.$resources.fetchDatabaseAccessInfo.fetch();
				},
				onError(error) {
					this.showChangePlanDialog = false;
					notify({
						title: error,
						icon: 'x',
						color: 'red'
					});
				}
			};
		}
	},
	computed: {
		databaseAccessInfo() {
			if (
				!this.$resources.fetchDatabaseAccessInfo.loading &&
				this.$resources.fetchDatabaseAccessInfo.data
			) {
				return this.$resources.fetchDatabaseAccessInfo.data;
			}
			return null;
		},
		dbAccessCommand() {
			if (this.databaseAccessInfo) {
				const { credentials } = this.databaseAccessInfo;
				return `mysql -u ${credentials.username} -p -h ${credentials.host} -P ${credentials.port} --ssl --ssl-verify-server-cert`;
			}
			return null;
		},
		plans() {
			let processedPlans = this.$resources.plans.data.map(plan => {
				if (!plan.database_access) {
					plan.disabled = true;
				}

				return plan;
			});

			return processedPlans;
		}
	},
	methods: {
		dialogClosed() {
			this.$emit('update:show', null);
		},
		pollDatabaseAccessJob(jobName) {
			this.pollingAgentJob = true;

			this.$call('press.api.site.get_job_status', {
				job_name: jobName
			}).then(message => {
				if (message.status === 'Success') {
					this.pollingAgentJob = false;
					this.$resources.fetchDatabaseAccessInfo.fetch();
				} else if (message.status === 'Failure') {
					this.pollingAgentJob = false;
					this.error = 'Something went wrong. Please try again.';
				} else {
					setTimeout(() => {
						this.pollDatabaseAccessJob(jobName);
					}, 1000);
				}
			});
		}
	}
};
</script>
