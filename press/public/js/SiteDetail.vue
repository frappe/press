<template>
	<div>
		<div>
			<div>{{ site.name }}</div>
			<div>{{ site.status }}</div>
		</div>
		<div>
			<div>
				<div>
					<div>Backups</div>
					<div>{{ site.backups.length }}</div>
				</div>
				<div>
					<div v-for="backup in site.backups" v-bind:key="backup.name">
						<div>{{ backup.name }}</div>
						<div>{{ backup.status }}</div>
						<div v-if="backup.status = 'In Progress'">{{ backup.progress }}</div>
						<div>{{ backup.size }}</div>
						<div>{{ backup.date }}</div>
					</div>
				</div>
				<div>
					<div>History</div>
				</div>
				<div>
					<div v-for="history in site.histories" v-bind:key="history.name">
						<div>{{ history.name }}</div>
						<div>{{ history.action }}</div>
						<div>{{ history.date }}</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: "SiteList",
	// props: ["site"],
	data() {
		return {
			site: {
				name: "erpnext.com",
				status: "Running",
				backups: [
					{
						name: "BACKUP-0003",
						size: "5.1 GB",
						date: "2019-11-28T03:24:00",
						status: "In Progress",
						progress: 30
					},
					{
						name: "BACKUP-0002",
						size: "4.5 GB",
						date: "2019-11-27T09:24:00",
						status: "Completed"
					},
					{
						name: "BACKUP-0001",
						size: "4.2 GB",
						date: "2019-11-27T03:24:00",
						status: "Completed"
					}
				],
				histories: [
					{
						name: "HISTORY-0006",
						date: "2019-11-28T03:24:00",
						action: "BACKUP"
					},
					{
						name: "HISTORY-0005",
						date: "2019-11-28T03:20:00",
						action: "DEPLOY"
					},
					{
						name: "HISTORY-0004",
						date: "2019-11-27T09:24:00",
						action: "BACKUP"
					},
					{
						name: "HISTORY-0003",
						date: "2019-11-27T03:24:00",
						action: "BACKUP"
					},
					{
						name: "HISTORY-0002",
						date: "2019-11-26T03:24:00",
						action: "DEPLOY"
					},
					{
						name: "HISTORY-0001",
						date: "2019-11-25T03:24:00",
						action: "CREATE"
					},
				]
			}
		};
	}
};
</script>
