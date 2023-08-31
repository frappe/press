<template>
	<div v-if="$resources.getPlan.data.monitor_access">
		<Card>
			<Report
				:title="`MariaDB Process List`"
				:columns="[
					{ label: 'ID', name: 'id', class: 'w-1/12' },
					{ label: 'User', name: 'user', class: 'w-1/12' },
					{ label: 'Time', name: 'time', class: 'w-1/12' },
					{ label: 'Command', name: 'command', class: 'w-1/12' },
					{ label: 'State', name: 'state', class: 'w-2/12' },
					{ label: 'Query', name: 'query', class: 'w-6/12' }
				]"
				:data="processData"
			>
				<template #actions>
					<Button @click="$resources.processList.reload()">Refresh</Button>
				</template>
			</Report>
			<div
				class="px-2 py-2 text-base text-gray-600"
				v-if="
					$resources.processList.loading &&
					$resources.processList.data.length == 0
				"
			>
				<LoadingText />
			</div>
			<div
				class="py-2 text-base text-gray-600"
				v-if="
					!$resources.processList.loading &&
					$resources.processList.data.length == 0
				"
			>
				No data
			</div>
		</Card>
	</div>
	<div class="flex justify-center" v-else>
		<span class="mt-16 text-base text-gray-700">
			Your plan doesn't support this feature. Please upgrade your plan.
		</span>
	</div>
</template>
<script>
import Report from '@/components/Report.vue';
export default {
	name: 'SiteMariaDBProcessList',
	props: ['site'],
	components: {
		Report
	},
	data() {
		return {
			max_lines: 20
		};
	},
	resources: {
		processList() {
			return {
				url: 'press.api.analytics.mariadb_processlist',
				params: {
					site: this.site?.name
				},
				auto: true,
				pageLength: this.max_lines,
				keepData: true,
				initialData: []
			};
		},
		getPlan() {
			return {
				url: 'press.api.site.current_plan',
				params: {
					name: this.site?.name
				},
				auto: true
			};
		}
	},
	computed: {
		processData() {
			let data = [];
			this.$resources.processList.data.forEach(row => {
				let out = [
					{ name: 'ID', value: row.Id, class: 'w-1/12' },
					{ name: 'User', value: row.User, class: 'w-1/12' },
					{ name: 'Time', value: row.Time, class: 'w-1/12' },
					{ name: 'Command', value: row.Command, class: 'w-1/12' },
					{ name: 'State', value: row.State, class: 'w-2/12' },
					{ name: 'Query', value: row.Info, class: 'w-6/12' }
				];
				data.push(out);
			});
			return data;
		}
	}
};
</script>
