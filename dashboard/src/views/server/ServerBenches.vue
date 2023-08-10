<template>
	<Table
		:columns="[
			{ label: 'Bench Name', name: 'name', width: 2 },
			{ label: 'Status', name: 'status' },
			{ label: 'Version', name: 'version' },
			{ label: 'Tags', name: 'tags' },
			{ label: 'Stats', name: 'stats' },
			{ label: '', name: 'actions', width: 0.5 }
		]"
		:rows="benches"
		v-slot="{ rows, columns }"
	>
		<TableHeader />
		<TableRow v-for="row in rows" :key="row.name" :row="row">
			<TableCell v-for="column in columns">
				<Badge
					class="ring-1 ring-white"
					v-if="column.name === 'status'"
					:label="row.status"
				/>
				<div v-else-if="column.name === 'tags'" class="-space-x-5">
					<Badge
						class="ring-1 ring-white"
						v-for="(tag, i) in row.tags.slice(0, 2)"
						:theme="$getColorBasedOnString(i)"
						:label="tag"
					/>
					<Badge
						class="ring-1 ring-white"
						v-if="row.tags.length > 2"
						:label="`+${row.tags.length - 2}`"
					/>
				</div>
				<div v-else-if="column.name === 'stats'" class="text-sm text-gray-600">
					{{
						`${row.stats.number_of_sites} ${$plural(
							row.stats.number_of_sites,
							'Site',
							'Sites'
						)}`
					}}
					&middot;
					{{
						`${row.stats.number_of_apps} ${$plural(
							row.stats.number_of_apps,
							'App',
							'Apps'
						)}`
					}}
				</div>
				<div v-else-if="column.name == 'actions'" class="w-full text-right">
					<Dropdown @click.prevent :options="dropdownItems(row)">
						<template v-slot="{ open }">
							<Button
								:variant="open ? 'subtle' : 'ghost'"
								class="mr-2"
								icon="more-horizontal"
							/>
						</template>
					</Dropdown>
				</div>
				<span v-else>{{ row[column.name] || '' }}</span>
			</TableCell>
		</TableRow>
	</Table>
</template>
<script>
import Table from '@/components/Table/Table.vue';
import TableCell from '@/components/Table/TableCell.vue';
import TableHeader from '@/components/Table/TableHeader.vue';
import TableRow from '@/components/Table/TableRow.vue';

export default {
	name: 'ServerBenches',
	components: {
		Table,
		TableHeader,
		TableRow,
		TableCell
	},
	props: ['server'],
	resources: {
		benches() {
			return {
				method: 'press.api.server.groups',
				params: {
					name: this.server?.name
				},
				auto: true
			};
		}
	},
	computed: {
		benches() {
			if (!this.$resources.benches.data) {
				return [];
			}

			return this.$resources.benches.data.map(bench => ({
				name: bench.title,
				status: bench.status,
				version: bench.version,
				stats: {
					number_of_sites: bench.number_of_sites,
					number_of_apps: bench.number_of_apps
				},
				tags: bench.tags,
				route: { name: 'BenchSiteList', params: { benchName: bench.name } }
			}));
		}
	},
	methods: {
		dropdownItems(bench) {
			return [
				{
					label: 'New Site',
					onClick: () => {
						this.$router.push(`/${bench.name}/new`);
					}
				},
				{
					label: 'View Versions',
					onClick: () => {
						this.$router.push(`/benches/${bench.name}/versions`);
					}
				}
			];
		}
	}
};
</script>
