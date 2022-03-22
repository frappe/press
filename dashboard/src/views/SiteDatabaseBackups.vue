<template>
	<Card
		v-if="site"
		title="Backups"
		subtitle="Backups are enabled and are scheduled to run every six hours."
	>
		<template #actions>
			<Button
				v-if="site?.status === 'Active'"
				@click="$resources.scheduleBackup.fetch()"
				:loading="$resources.scheduleBackup.loading"
			>
				Schedule a backup now
			</Button>
		</template>
		<div class="divide-y" v-if="backups.data.length">
			<div
				class="flex items-center justify-between py-2"
				v-for="backup in backups.data"
				:key="backup.database_url"
			>
				<div class="text-base">
					<span
						v-if="backup.status === 'Success'"
						class="flex items-center justify-between"
					>
						<span>
							Backup on <FormatDate>{{ backup.creation }}</FormatDate>
						</span>
					</span>
					<span v-else> Performing Backup... </span>
				</div>
				<div class="flex items-center space-x-2">
					<Badge v-if="backup.offsite" color="green"> Offsite </Badge>
					<Dropdown :items="dropdownItems(backup)" right>
						<template v-slot="{ toggleDropdown }">
							<Button icon="more-horizontal" @click="toggleDropdown()" />
						</template>
					</Dropdown>
				</div>
			</div>
		</div>
		<div class="mt-2 text-base text-gray-600" v-else>
			<Button
				v-if="$resources.backups.loading"
				:loading="true"
				loading-text="Loading"
			/>
			<span v-else> No backups found </span>
		</div>
	</Card>
</template>
<script>
export default {
	name: 'SiteDatabaseBackups',
	props: ['site'],
	data() {
		return {
			isRestorePending: false,
			backupToRestore: null
		};
	},
	resources: {
		backups() {
			return {
				method: 'press.api.site.backups',
				params: {
					name: this.site?.name
				},
				default: [],
				auto: true
			};
		},
		scheduleBackup() {
			return {
				method: 'press.api.site.backup',
				params: {
					name: this.site?.name,
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
	computed: {
		backups() {
			return this.$resources.backups;
		}
	},
	methods: {
		dropdownItems(backup) {
			return [
				{
					label: 'Download',
					isGroup: true
				},
				{
					label: `Database (${this.formatBytes(backup.database_size || 0)})`,
					action: () => {
						this.downloadBackup(
							backup.name,
							'database',
							backup.database_url,
							backup.offsite
						);
					}
				},
				{
					label: `Public Files (${this.formatBytes(backup.public_size || 0)})`,
					condition: () => backup.public_file,
					action: () => {
						this.downloadBackup(
							backup.name,
							'public',
							backup.public_url,
							backup.offsite
						);
					}
				},
				{
					label: `Private Files (${this.formatBytes(
						backup.private_size || 0
					)})`,
					condition: () => backup.private_file,
					action: () => {
						this.downloadBackup(
							backup.name,
							'private',
							backup.private_url,
							backup.offsite
						);
					}
				},
				{
					label: 'Actions',
					isGroup: true,
					condition: () => backup.offsite
				},
				{
					label: 'Restore',
					condition: () => backup.offsite,
					action: () => {
						this.$confirm({
							title: 'Restore Backup',
							// prettier-ignore
							message: `Are you sure you want to restore your site to <b>${this.formatDate(backup.creation)}</b>?`,
							actionLabel: 'Restore',
							actionType: 'primary',
							action: closeDialog => {
								closeDialog();
								this.restoreOffsiteBackup(backup);
							}
						});
					}
				}
			].filter(d => (d.condition ? d.condition() : true));
		},
		async downloadBackup(name, file, database_url, offsite) {
			let link = offsite
				? await this.$call('press.api.site.get_backup_link', {
						name: this.site.name,
						backup: name,
						file: file
				  })
				: database_url;
			window.open(link);
		},
		async restoreOffsiteBackup(backup) {
			this.isRestorePending = true;
			this.$call('press.api.site.restore', {
				name: this.site.name,
				files: {
					database: backup.remote_database_file,
					public: backup.remote_public_file,
					private: backup.remote_private_file
				}
			}).then(() => {
				this.isRestorePending = false;
				this.$router.push(`/sites/${this.site.name}/jobs`);
				setTimeout(() => {
					window.location.reload();
				}, 1000);
			});
		}
	}
};
</script>
