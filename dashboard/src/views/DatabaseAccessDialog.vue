<template>
	<Dialog
		v-if="site"
		:modelValue="Boolean(site) && show"
		title="Access Database"
		:dismissable="true"
		@close="dialogClosed"
	>
		<Button
			v-if="$resources.fetchDatabaseAccessInfo.loading"
			:loading="$resources.fetchDatabaseAccessInfo.loading"
			>Loading</Button
		>
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
				<div class="pt-4 pb-2">
					<p class="mb-2 text-base font-semibold text-gray-700">
						Using MariaDB Client
					</p>
					<p class="mb-2 text-base">
						<span
							>Run this command in your terminal to access MariaDB console</span
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
			return null;
		},
		dbAccessCommand() {
			if (this.databaseAccessInfo) {
				const { credentials } = this.databaseAccessInfo;
				return `mysql -u ${credentials.username} -p${credentials.password} -h ${credentials.host} -P ${credentials.port} --ssl --ssl-verify-server-cert`;
			}
			return null;
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
				} else if (
					message.status === 'Failure' ||
					message.status === 'Undelivered'
				) {
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
