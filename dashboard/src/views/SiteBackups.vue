<template>
	<div>
		<section>
			<h2 class="font-medium text-lg">Backups</h2>
			<p class="text-gray-600">Backups are enabled and are scheduled every week at 12:00 AM</p>
			<div class="mt-6 w-1/2 shadow rounded border border-gray-100 px-6 py-4">
				<div>
					<div
						class="grid grid-cols-4 items-start py-4"
						v-for="backup in backups"
					>
						<div class="col-span-3">
							<div class="font-semibold ">{{ backup.name }}</div>
							<div class="text-gray-600 text-sm">
								<FormatDate>{{ backup.creation }}</FormatDate>
							</div>
						</div>
						<div class="text-right text-sm">
							<a :href="backup.url" class="text-brand">Download</a>
						</div>
					</div>
				</div>
				<div class="mt-4">
					<Button class="bg-brand hover:bg-blue-600 text-white">Schedule Backup</Button>
					<Button class="ml-4 border hover:bg-gray-100">Disable Backups</Button>
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
			backups: [
				{
					creation: '2020-02-23 18:38:37',
					name: '20200223_183837-frappe-cloud-database.sql.gz',
					url: `http:${this.site.name}/private/backups/20200223_183837-frappe-cloud-database.sql.gz`
				},
				{
					creation: '2020-02-20 12:01:09',
					name: '20200220_120109-frappe-cloud-database.sql.gz',
					url: `http:${this.site.name}/private/backups/20200223_183837-frappe-cloud-database.sql.gz`
				}
			]
		};
	}
};
</script>
