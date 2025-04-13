<template>
	<Dialog
		:options="{
			title: 'Query Logs',
			size: '2xl'
		}"
	>
		<template #body-content>
			<ObjectList :options="listOptions" v-if="!selectedRow" />
			<div v-else>
				<div class="flex flex-row items-center justify-between">
					<Button icon="arrow-left" @click="selectedRow = null">Back</Button>
					<Button variant="outline" iconLeft="play" @click="rerunQuery"
						>Re-run Query</Button
					>
				</div>
				<div class="mt-4">
					<p class="text-sm text-gray-600">Query</p>
					<pre
						class="mt-1.5 max-h-52 overflow-y-auto whitespace-pre-wrap rounded bg-gray-50 px-2 py-1.5 text-sm text-gray-600"
						>{{ selectedRow.query }}</pre
					>
				</div>
				<div class="mt-3">
					<p class="text-sm text-gray-600">Timestamp</p>
					<p class="mt-1.5 text-sm text-gray-700">
						{{ new Date(selectedRow.creation).toLocaleString() }}
					</p>
				</div>
				<div class="mt-3">
					<p class="text-sm text-gray-600">Committed in DB</p>
					<p class="mt-1.5 text-sm text-gray-700">
						{{ selectedRow.committed ? 'Yes' : 'No' }}
					</p>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script>
import ObjectList from '../../ObjectList.vue';
export default {
	name: 'DatabaseSQLPlaygroundLog',
	props: ['site'],
	emits: ['rerunQuery'],
	components: {
		ObjectList
	},
	data() {
		return {
			selectedRow: null
		};
	},
	computed: {
		listOptions() {
			return {
				url: 'press.api.client.get_list',
				doctype: 'SQL Playground Log',
				filters: {
					site: this.site
				},
				fields: ['query', 'committed', 'creation'],
				pageLength: 10,
				orderBy: 'creation desc',
				emptyStateMessage: 'No Logs found.',
				columns: [
					{
						label: 'Query',
						width: 2,
						fieldname: 'query',
						format(value) {
							if (value.length > 40) {
								return value.substring(0, 40) + '...';
							}
							return value;
						}
					},
					{
						label: 'Timestamp',
						width: 1,
						align: 'center',
						fieldname: 'creation',
						format(value) {
							return new Date(value).toLocaleString();
						}
					},
					{
						label: 'Committed',
						fieldname: 'committed',
						align: 'center',
						width: 0.5,
						type: 'Icon',
						Icon(value) {
							return value ? 'check' : 'x';
						}
					}
				],
				onRowClick: row => {
					this.selectedRow = row;
				}
			};
		}
	},
	methods: {
		rerunQuery() {
			const query = this.selectedRow.query;
			this.selectedRow = null;
			this.$emit('rerunQuery', query);
		}
	}
};
</script>
