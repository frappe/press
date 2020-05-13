<template>
	<div>
		<Section
			title="Backups"
			description="Backups are enabled and are scheduled to run every six hours."
		>
			<SectionCard class="sm:w-2/3">
				<div v-if="backups.data.length">
					<a
						:href="backup.url"
						target="_blank"
						class="block px-6 py-4 hover:bg-gray-50"
						v-for="backup in backups.data"
						:key="backup.url"
					>
						<div class="w-full">
							<a
								class="flex items-baseline justify-between w-full font-semibold"
							>
								<span>
									{{ backup.database || 'Performing backup..' }}
								</span>
								<span class="font-normal text-gray-700" v-if="backup.size">
									{{ formatBytes(backup.size) }}
								</span>
							</a>
							<div class="text-sm text-gray-600" v-if="backup.database">
								<FormatDate>{{ backup.creation }}</FormatDate>
							</div>
						</div>
					</a>
				</div>
				<div class="px-6 mt-2 text-gray-600" v-else>
					No backups found
				</div>
				<div class="px-6 mt-4 mb-2">
					<Button
						type="primary"
						@click="$resources.scheduleBackup.fetch()"
						:disabled="$resources.scheduleBackup.loading"
					>
						Schedule Backup
					</Button>
				</div>
			</SectionCard>
		</Section>
	</div>
</template>

<script>
export default {
	name: 'SiteBackups',
	props: ['site'],
	resources: {
		backups() {
			return {
				method: 'press.api.site.backups',
				params: {
					name: this.site.name
				},
				default: [],
				auto: true
			};
		},
		scheduleBackup() {
			return {
				method: 'press.api.site.backup',
				params: {
					name: this.site.name
				},
				onSuccess: () => {
					this.$resources.backups.reload();
				}
			};
		}
	},
	mounted() {
		this.$store.socket.on('agent_job_update', data => {
			if (data.site === this.site.name && data.name === 'Backup Site') {
				if (data.status === 'Success') {
					this.$resources.backups.reload();
				}
			}
		});
	},
	methods: {
		formatBytes(bytes, decimals = 2) {
			if (bytes === 0) return '0 Bytes';

			const k = 1024;
			const dm = decimals < 0 ? 0 : decimals;
			const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

			const i = Math.floor(Math.log(bytes) / Math.log(k));

			return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
		}
	}
};
</script>
