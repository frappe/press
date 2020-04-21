<template>
	<div>
		<section>
			<h2 class="font-medium text-lg">Backups</h2>
			<p class="text-gray-600">
				Backups are enabled and are scheduled to run every six hours.
			</p>
			<div
				class="mt-6 w-full sm:w-1/2 shadow rounded border border-gray-100 py-4"
			>
				<div v-if="backups.length">
					<a
						:href="backup.url"
						target="_blank"
						class="px-6 py-4 hover:bg-gray-50 block"
						v-for="backup in backups"
					>
						<div class="w-full">
							<a
								class="w-full flex font-semibold justify-between items-baseline"
							>
								<span>
									{{ backup.database || 'Performing backup..' }}
								</span>
								<span class="text-gray-700 font-normal" v-if="backup.size">
									{{ formatBytes(backup.size) }}
								</span>
							</a>
							<div class="text-gray-600 text-sm" v-if="backup.database">
								<FormatDate>{{ backup.creation }}</FormatDate>
							</div>
						</div>
					</a>
				</div>
				<div class="px-6 text-gray-600" v-else>
					No backups found
				</div>
				<div class="px-6 mt-4">
					<Button type="primary" @click="scheduleBackup">
						Schedule Backup
					</Button>
				</div>
			</div>
		</section>
	</div>
</template>

<script>
export default {
	name: 'SiteBackups',
	props: ['site'],
	data() {
		return {
			backups: []
		};
	},
	mounted() {
		this.fetchBackups();
		this.$store.socket.on('agent_job_update', data => {
			if (data.site === this.site.name && data.name === 'Backup Site') {
				if (data.status === 'Success') {
					this.fetchBackups();
				}
			}
		});
	},
	methods: {
		async fetchBackups() {
			this.backups = await this.$call('press.api.site.backups', {
				name: this.site.name
			});
		},
		async scheduleBackup() {
			await this.$call('press.api.site.backup', {
				name: this.site.name
			});
			this.fetchBackups();
		},
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
