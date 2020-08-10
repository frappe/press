<template>
	<div>
		<Section
			title="Backups"
			description="Backups are enabled and are scheduled to run every six hours."
		>
			<SectionCard class="sm:w-1/2">
				<div v-if="backups.data.length">
					<div
						class="block px-6 py-4 text-base hover:bg-gray-50"
						v-for="backup in backups.data"
						:key="backup.database_url"
					>
						<div class="w-full">
							<div class="font-semibold">
								<span
									v-if="backup.status === 'Success'"
									class="flex justify-between items-center"
								>
									<span>
										Backup on <FormatDate>{{ backup.creation }}</FormatDate>
									</span>
									<Badge v-if="backup.offsite" class="ml-4" color="green">
										Offsite
									</Badge>
								</span>
								<span v-else>
									Performing Backup...
								</span>
							</div>
							<div
								v-if="backup.status === 'Success'"
								class="grid grid-cols-3 mt-2"
							>
								<div>
									<button
										v-on:click="
											downloadBackup(
												backup.name,
												'database',
												backup.database_url,
												backup.offsite
											)
										"
										class="text-gray-800 border-b border-gray-500"
									>
										Database ({{ formatBytes(backup.database_size) }})
									</button>
								</div>
								<div>
									<button
										v-on:click="
											downloadBackup(
												backup.name,
												'private',
												backup.private_url,
												backup.offsite
											)
										"
										class="text-gray-800 border-b border-gray-500"
										v-if="backup.private_file"
									>
										Private Files ({{ formatBytes(backup.private_size) }})
									</button>
								</div>
								<div>
									<button
										v-on:click="
											downloadBackup(
												backup.name,
												'public',
												backup.public_url,
												backup.offsite
											)
										"
										class="text-gray-800 border-b border-gray-500"
										v-if="backup.public_file"
									>
										Public Files ({{ formatBytes(backup.public_size) }})
									</button>
								</div>
							</div>
						</div>
					</div>
				</div>
				<div class="px-6 mt-2 text-base text-gray-600" v-else>
					No backups found
				</div>
				<div class="px-6 mt-4 mb-2">
					<Button
						type="primary"
						@click="$resources.scheduleBackup.fetch()"
						:disabled="$resources.scheduleBackup.loading"
					>
						Schedule Backup with Files
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
					name: this.site.name,
					with_files: true
				},
				onSuccess: () => {
					this.$resources.backups.reload();
				}
			};
		}
	},
	mounted() {
		this.$socket.on('agent_job_update', data => {
			if (data.site === this.site.name && data.name === 'Backup Site') {
				if (data.status === 'Success') {
					this.$resources.backups.reload();
				}
			}
		});
	},
	methods: {
		async downloadBackup(name, file, database_url, offsite) {
			let link = offsite
				? await this.$call('press.api.site.get_backup_link', {
						backup: name,
						file: file
				  })
				: database_url;
			window.open(link);
		}
	}
};
</script>
