<template>
	<Dialog
		v-if="site"
		:show="Boolean(site) && show"
		title="Access Site Database"
		:dismissable="true"
		v-on:close="dialogClosed"
	>
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
				<p class="mt-3 text-sm">
					Note: You should have a <span class="font-mono">mysql</span> client
					installed on your computer.
				</p>
			</div>
			<div v-else>
				<p class="mb-2 text-sm">
					Database console access is disabled for this site.
				</p>
			</div>
		</div>

		<ErrorMessage class="mt-3" :error="$resourceErrors || error" />

		<div class="mt-2">
			<Button
				v-if="
					databaseAccessInfo && !databaseAccessInfo.is_database_access_enabled
				"
				@click="$resources.enableDatabaseAccess.submit()"
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
	props: ['site', 'show'],
	data() {
		return {
			pollingAgentJob: false,
			error: null
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
					this.pollDatabaseAccessJob(d);
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
					this.pollDatabaseAccessJob(d);
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
				} else if (
					message.status === 'Failure' ||
					message.status === 'Undelivered'
				) {
					this.pollingAgentJob = false;
					this.error = 'Something went wrong. Please try again.';
				} else {
					setTimeout(() => {
						this.pollDatabaseAccessJob(jobName);
					}, 300);
				}
			});
		}
	}
};
</script>
