<template>
	<Dialog v-if="site" :show="Boolean(site)" title="Access Site Database">
		<Button
			v-if="$resources.fetchDatabaseAccessInfo.loading"
			:loading="$resources.fetchDatabaseAccessInfo.loading"
			>Loading</Button
		>
		<div v-if="databaseAccessInfo">
			<div v-if="databaseAccessInfo.is_database_access_enabled">
				<p class="mb-2 text-sm">
					Copy and paste this command in your terminal:
				</p>
				<ClickToCopyField :textContent="dbAccessCommand" />
				<p class="mt-2 text-sm">
					Note: You should have a <span class="font-mono">mysql</span> client
					installed on your computer.
				</p>
			</div>
			<div v-else>
				<p class="mb-2 text-sm">Database access is disabled for this site.</p>
			</div>
		</div>

		<div class="mt-3">
			<Button
				v-if="
					databaseAccessInfo && !databaseAccessInfo.is_database_access_enabled
				"
				@click="enableDatabaseAccess"
				:loading="$resources.enableDatabaseAccess.loading || pollingAgentJob"
				type="primary"
				>Enable Access</Button
			>

			<Button
				v-if="
					databaseAccessInfo && databaseAccessInfo.is_database_access_enabled
				"
				@click="$resources.disableDatabaseAccess.submit()"
				:loading="$resources.disableDatabaseAccess.loading || pollingAgentJob"
				>Disable Access</Button
			>
		</div>
	</Dialog>
</template>

<script>
import ClickToCopyField from '@/components/ClickToCopyField.vue';

export default {
	data() {
		return {
			site: 'jsdhfjdf.h.fc.frappe.dev', // TODO: Convert to prop later
			pollingAgentJob: false
		};
	},
	components: {
		ClickToCopyField
	},
	resources: {
		fetchDatabaseAccessInfo() {
			return {
				method: 'press.api.site.get_database_access_info',
				params: {
					name: this.site
				},
				auto: true
			};
		},
		enableDatabaseAccess() {
			return {
				method: 'press.api.site.enable_database_access',
				params: {
					name: this.site
				},
				onSuccess(d) {
					this.pollEnableDatabaseAccessJob(d);
				}
			};
		},
		disableDatabaseAccess() {
			return {
				method: 'press.api.site.disable_database_access',
				params: {
					name: this.site
				},
				onSuccess(d) {
					this.pollEnableDatabaseAccessJob(d);
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
		},
		dbAccessCommand() {
			if (this.databaseAccessInfo) {
				const { credentials } = this.databaseAccessInfo;
				return `mysql -u ${credentials.username} -p${credentials.password} -h ${credentials.host} -P ${credentials.port} --ssl --ssl-verify-server-cert`;
			}
		}
	},
	components: { ClickToCopyField },
	methods: {
		enableDatabaseAccess() {
			this.$resources.enableDatabaseAccess.submit();
		},
		pollEnableDatabaseAccessJob(jobName) {
			this.pollingAgentJob = true;

			this.$call('press.api.site.get_job_status', {
				job_name: jobName
			}).then(message => {
				if (message.status === 'Success') {
					this.pollingAgentJob = false;
					this.$resources.fetchDatabaseAccessInfo.fetch();
				} else if (message.status === 'Failure') {
					this.pollingAgentJob = false;
					// TODO: Show some error message
				} else {
					console.log('Polling again...', jobName);
					setTimeout(() => {
						this.pollEnableDatabaseAccessJob(jobName);
					}, 300);
				}
			});
		}
	}
};
</script>
