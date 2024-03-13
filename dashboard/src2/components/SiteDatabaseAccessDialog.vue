<template>
	<Dialog :options="{ title: 'Manage Database Access' }" v-model="show">
		<template #body-content>
			<!-- Not available on current plan, upsell higher plans -->
			<div v-if="!sitePlan?.database_access">
				<div>
					<p class="text-base">
						Database access is not available on your current plan. Please
						upgrade to a higher plan to use this feature.
					</p>

					<Button
						class="mt-4 w-full"
						variant="solid"
						@click="showChangePlanDialog = true"
					>
						Upgrade Site Plan
					</Button>
					<ManageSitePlansDialog :site="site" v-if="showChangePlanDialog" />
				</div>
			</div>

			<!-- Available on the current plan -->
			<div v-else>
				<div v-if="$site.doc.is_database_access_enabled">
					<div v-if="databaseCredentials">
						<p class="mb-2 text-base font-semibold text-gray-700">
							Using an Analytics or Business Intelligence Tool
						</p>
						<p class="mb-2 text-base">
							Use following credentials with your analytics or business
							intelligence tool
						</p>
						<p class="ml-1 font-mono text-sm">
							Host: {{ databaseCredentials.host }}
						</p>
						<p class="ml-1 font-mono text-sm">
							Port: {{ databaseCredentials.port }}
						</p>
						<p class="ml-1 font-mono text-sm">
							Database Name: {{ databaseCredentials.database }}
						</p>
						<p class="ml-1 font-mono text-sm">
							Username: {{ databaseCredentials.username }}
						</p>
						<p class="ml-1 font-mono text-sm">
							Password: {{ databaseCredentials.password }}
						</p>
					</div>
					<div class="pb-2 pt-5">
						<p class="mb-2 text-base font-semibold text-gray-700">
							Using MariaDB Client
						</p>
						<p class="mb-2 text-base">
							Run this command in your terminal to access MariaDB console
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
					<p class="mb-2 text-sm">Database access is disabled for this site.</p>
				</div>

				<div class="mt-4">
					<div
						v-if="planSupportsDatabaseAccess && !databaseAccessEnabled"
						class="mb-2"
					>
						<FormControl
							label="Access type"
							type="select"
							:options="[
								{ label: 'Read only', value: 'read_only' },
								{ label: 'Read & Write', value: 'read_write' }
							]"
							v-model="mode"
						/>
						<p v-if="mode === 'read_write'" class="mt-2 text-base text-red-600">
							Your credentials can be used to modify or wipe your database
						</p>
					</div>
					<ErrorMessage
						class="mt-2"
						:message="
							$site.enableDatabaseAccess.error ||
							$site.disableDatabaseAccess.error ||
							error
						"
					/>
					<Button
						v-if="planSupportsDatabaseAccess && !databaseAccessEnabled"
						@click="enableDatabaseAccess"
						:loading="
							$site.enableDatabaseAccess.loading || pollingAgentJob?.loading
						"
						variant="solid"
						class="mt-2 w-full"
					>
						Enable Access
					</Button>
					<Button
						v-if="planSupportsDatabaseAccess && databaseAccessEnabled"
						@click="$site.disableDatabaseAccess.submit()"
						:loading="$site.disableDatabaseAccess.loading"
						class="w-full"
					>
						Disable Access
					</Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script>
import { defineAsyncComponent } from 'vue';
import { getCachedDocumentResource } from 'frappe-ui';
import ClickToCopyField from '../../src/components/ClickToCopyField.vue';
import { pollJobStatus } from '../utils/agentJob';
import { getPlan } from '../data/plans';

export default {
	name: 'SiteDatabaseAccessDialog',
	props: ['site'],
	components: {
		ManageSitePlansDialog: defineAsyncComponent(() =>
			import('./ManageSitePlansDialog.vue')
		),
		ClickToCopyField
	},
	data() {
		return {
			mode: 'read_only',
			show: true,
			showChangePlanDialog: false,
			error: null,
			pollingAgentJob: null
		};
	},
	mounted() {
		this.fetchDatabaseCredentials();
	},
	methods: {
		enableDatabaseAccess() {
			return this.$site.enableDatabaseAccess.submit(
				{ mode: this.mode },
				{
					onSuccess: result => {
						let jobId = result.message;
						this.pollingAgentJob = pollJobStatus(jobId, status => {
							if (status === 'Success') {
								this.fetchDatabaseCredentials();
								return true;
							} else if (status === 'Failure') {
								this.error = 'Failed to enable database access';
								return true;
							}
						});
					}
				}
			);
		},
		fetchDatabaseCredentials() {
			if (this.planSupportsDatabaseAccess && this.databaseAccessEnabled) {
				this.$site.getDatabaseCredentials.fetch();
			}
		}
	},
	computed: {
		databaseCredentials() {
			return this.$site.getDatabaseCredentials.data;
		},
		databaseAccessEnabled() {
			return this.$site.doc.is_database_access_enabled;
		},
		planSupportsDatabaseAccess() {
			return this.sitePlan?.database_access;
		},
		sitePlan() {
			return getPlan(this.$site.doc.plan);
		},
		$site() {
			return getCachedDocumentResource('Site', this.site);
		}
	}
};
</script>
