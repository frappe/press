<template>
	<div class="mx-5">
		<div class="pb-20">
			<div class="flex">
				<div class="flex w-full space-x-2 pb-4">
					<FormControl
						label="Search Sites"
						v-model="searchTerm"
						v-if="!disableSearch"
					>
						<template #prefix>
							<FeatherIcon name="search" class="w-4 text-gray-600" />
						</template>
					</FormControl>
				</div>
			</div>
			<Table
				:columns="[
					{ label: 'Protocol', name: 'protocol' },
					{ label: 'Port Range', name: 'port_range' },
					{ label: 'Source', name: 'source' },
					{ label: 'Action', name: 'action' },
					{ label: 'Description', name: 'description', width: 2 },
					{ label: '', name: 'actions', width: 0.5 }
				]"
				:rows="rules"
				v-slot="{ rows, columns }"
			>
				<TableHeader />
				<TableRow v-for="row in rows" :key="row.name" :row="row">
					<TableCell v-for="column in columns">
						<div
							v-if="column.name == 'actions' && !disableAction"
							class="w-full text-right"
						>
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
						<span>{{ row[column.name] || '' }}</span>
					</TableCell>
				</TableRow>
			</Table>
		</div>
	</div>
</template>

<script>
import Table from '@/components/Table/Table.vue';
import TableHeader from '@/components/Table/TableHeader.vue';
import TableRow from '@/components/Table/TableRow.vue';
import TableCell from '@/components/Table/TableCell.vue';

export default {
	name: 'FirewallRuleView',
	props: ['servers', 'rules', 'disableAction', 'disableSearch'],
	components: {
		Table,
		TableHeader,
		TableRow,
		TableCell
	},
	methods: {
		dropdownItems(rule) {
			return [
				{
					label: 'Delete Rule',
					onClick: () => {
						this.rules.splice(this.rules.indexOf(rule), 1);
					}
				}
			];
		}
	}
};
</script>
