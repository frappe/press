<template>
	<div>
		<section>
			<h2 class="font-medium text-lg">Backups</h2>
			<p class="text-gray-600">
				Backups are enabled and are scheduled every week at 12:00 AM
			</p>
			<div class="mt-6 w-1/2 shadow rounded border border-gray-100 px-6 py-4">
				<div v-if="backups.length">
					<div class="py-4" v-for="backup in backups">
						<div>
							<a
								:href="backup.url"
								target="_blank"
								class="flex font-semibold justify-between items-baseline"
							>
								<span>
									{{ backup.database }}
								</span>
								<span class="text-gray-700 font-normal">
									{{ formattedSize(backup.size) }}
								</span>
							</a>
							<div class="text-gray-600 text-sm">
								<FormatDate>{{ backup.creation }}</FormatDate>
							</div>
						</div>
					</div>
				</div>
				<div class="text-gray-600" v-else>
					No backups found
				</div>
				<div class="mt-4">
					<Button
						class="bg-brand hover:bg-blue-600 text-white"
						@click="scheduleBackup"
					>
						Schedule Backup
					</Button>
					<Button class="ml-4 border hover:bg-gray-100">
						Disable Backups
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
	},
	methods: {
		async fetchBackups() {
			this.backups = await this.$call('frappe.client.get_list', {
				doctype: 'Site Backup',
				fields: '`name`, `database`, `size`, `creation`, `url`',
				filters: {
					site: this.site.name
				}
			});
		},
		async scheduleBackup() {
			await this.$call('press.api.site.schedule_backup', {
				name: this.site.name
			});
			this.fetchBackups();
		},
		formattedSize(size) {
			return Math.floor(size / 1024) + 'MB';
		}
	}
};
</script>
