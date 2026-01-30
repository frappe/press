<template>
	<div class="flex flex-1 flex-shrink-0 flex-col overflow-hidden">
		<div class="relative flex h-full w-full flex-col overflow-hidden">
			<div>
				<div class="mb-4 flex justify-between">
					<div class="space-x-2">
						<FormControl
							type="select"
							label="Filter By Level"
							:options="[
								{ label: 'All', value: '' },
								{ label: 'Info', value: 'Info' },
								{ label: 'Warning', value: 'warning' },
								{ label: 'Error', value: 'error' },
								{ label: 'Critical', value: 'critical' },
							]"
							class="w-24"
							v-if="columns.includes('level')"
							v-model="levelFilter"
						/>
					</div>
					<div class="flex space-x-2">
						<FormControl
							type="select"
							label="Sort By"
							:options="[
								{ label: 'Sort By', disabled: true },
								{ label: 'Newest First', value: 'desc' },
								{ label: 'Oldest First', value: 'asc' },
							]"
							class="w-32"
							v-if="columns.includes('time')"
							v-model="sortOrder"
						/>
						<FormControl
							class="w-80"
							label="Search log"
							v-model="searchLogQuery"
						>
							<template #prefix>
								<lucide-search class="h-4 w-4 text-gray-500" />
							</template>
						</FormControl>
					</div>
				</div>
				<div
					class="flex h-[81.5vh] w-full flex-col overflow-hidden rounded border"
				>
					<div class="relative flex flex-1 flex-col overflow-auto">
						<table
							v-if="columns?.length || props.log?.length"
							class="w-full border-separate border-spacing-0"
						>
							<thead class="z-5 sticky top-0 z-10 w-full rounded bg-gray-100">
								<tr
									v-for="headerGroup in table.getHeaderGroups()"
									:key="headerGroup.id"
								>
									<th
										v-for="header in headerGroup.headers"
										:key="header.id"
										:colSpan="header.colSpan"
										class="text-gray-800"
										:class="{
											'w-2/12': header.column.columnDef.id === 'level',
											'w-3/12': header.column.columnDef.id === 'time',
										}"
									>
										<div
											class="flex items-center truncate px-3 py-2 text-base font-semibold"
										>
											<FlexRender
												v-if="!header.isPlaceholder"
												:render="header.column.columnDef.header"
												:props="header.getContext()"
											/>
										</div>
									</th>
								</tr>
							</thead>
							<tbody>
								<template
									v-for="(row, index) in table.getRowModel().rows"
									:key="row.id"
								>
									<tr class="hover:bg-gray-50">
										<td
											v-for="cell in row.getVisibleCells()"
											:key="cell.id"
											class="max-w-[35rem] cursor-pointer truncate border-b px-3 py-2"
											:class="{
												'border-b-0': row.getIsExpanded(),
											}"
											@click="handleExpand(row)"
										>
											<div
												v-if="cell.column.columnDef.id === 'level'"
												class="flex items-center space-x-2"
											>
												<lucide-info
													v-if="getBadgeLabel(cell) === 'Info'"
													class="h-4 w-4 text-blue-500"
												/>
												<lucide-alert-triangle
													v-else-if="getBadgeLabel(cell) === 'Warning'"
													class="h-4 w-4 text-yellow-500"
												/>
												<lucide-alert-circle
													v-else-if="
														getBadgeLabel(cell) === 'Error' ||
														getBadgeLabel(cell) === 'Critical'
													"
													class="h-4 w-4 text-red-500"
												/>
												<span
													class="text-xs"
													:class="{
														'text-blue-500': getBadgeLabel(cell) === 'Info',
														'text-yellow-500':
															getBadgeLabel(cell) === 'Warning',
														'text-red-500':
															getBadgeLabel(cell) === 'Error' ||
															getBadgeLabel(cell) === 'Critical',
													}"
													>{{ getBadgeLabel(cell) }}</span
												>
											</div>
											<div
												v-else
												class="truncate font-mono text-sm"
												:class="{
													'font-mono ': cell.column.columnDef.id === 'time',
													'font-mono text-gray-600':
														cell.column.columnDef.id === 'description',
												}"
											>
												<FlexRender
													:render="cell.column.columnDef.cell"
													:props="cell.getContext()"
												/>
											</div>
										</td>
									</tr>
									<tr>
										<td
											v-if="row.getIsExpanded()"
											:colspan="row.getAllCells().length"
											class="max-w-[39.75rem] whitespace-pre-wrap break-words border-b bg-gray-900 px-3 py-4 font-mono text-sm text-gray-200"
										>
											{{ row.original.description }}
										</td>
									</tr>
								</template>
								<tr height="99%" class="border-b"></tr>
							</tbody>
						</table>

						<div v-if="table.getRowModel().rows.length === 0" class="p-8">
							<p class="text-center text-sm text-gray-500">
								No log entries found
							</p>
						</div>
					</div>

					<div class="flex justify-between rounded rounded-t-none border-t p-1">
						<div></div>
						<div class="flex flex-shrink-0 items-center justify-end gap-3">
							<p class="tnum text-sm text-gray-600">
								{{ pageStart }} - {{ pageEnd }} of {{ totalRows }} rows
							</p>
							<div class="flex gap-2">
								<Button
									variant="ghost"
									@click="table.previousPage()"
									:disabled="!table.getCanPreviousPage()"
									iconLeft="arrow-left"
								>
									Prev
								</Button>
								<Button
									variant="ghost"
									@click="table.nextPage()"
									:disabled="!table.getCanNextPage()"
									iconRight="arrow-right"
								>
									Next
								</Button>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import {
	FlexRender,
	getCoreRowModel,
	getSortedRowModel,
	getFilteredRowModel,
	getExpandedRowModel,
	getPaginationRowModel,
	useVueTable,
} from '@tanstack/vue-table';
import { computed, ref } from 'vue';

const props = defineProps({
	log: {
		type: Array,
		required: true,
	},
});

const searchLogQuery = ref('');
const levelFilter = ref('');
const sortOrder = ref('desc');

const columnFilters = computed(() => {
	const filters = [];
	if (levelFilter.value) {
		filters.push({
			id: 'level',
			value: levelFilter.value,
		});
	}
	if (searchLogQuery.value) {
		filters.push({
			id: 'description',
			value: searchLogQuery.value,
		});
	}
	return filters;
});

const logEntries = computed(() => props.log);
const columns = computed(() => {
	const columns = Object.keys(logEntries.value[0] || {});
	columns.sort((a, b) => {
		if (a === 'description') return 1;
		if (b === 'description') return -1;
		return 0;
	});

	return columns.length ? columns : ['description'];
});
const sortingState = computed(() => {
	if (!sortOrder.value) return [];
	return [
		{
			id: 'time',
			desc: sortOrder.value === 'desc',
		},
	];
});

const table = useVueTable({
	data: logEntries.value,
	columns: columns.value.map((column) => {
		return {
			id: column,
			header: capitalizeFirstLetter(column),
			accessorKey: column,
			enableSorting: column === 'time' ? true : false,
			sortingFn: column === 'time' ? 'datetime' : null,
			isNumber: false,
		};
	}),
	state: {
		get columnFilters() {
			return columnFilters.value;
		},
		get sorting() {
			return sortingState.value;
		},
	},
	initialState: {
		pagination: {
			pageSize: 20,
			pageIndex: 0,
		},
	},
	// debugTable: true, // Uncomment to see the table state in the console
	getRowCanExpand: (_row) => true,
	getCoreRowModel: getCoreRowModel(),
	getSortedRowModel: getSortedRowModel(),
	getExpandedRowModel: getExpandedRowModel(),
	getFilteredRowModel: getFilteredRowModel(),
	getPaginationRowModel: getPaginationRowModel(),
});

const pageLength = computed(() => table.getState().pagination.pageSize);
const currPage = computed(() => table.getState().pagination.pageIndex + 1);

const totalRows = computed(() => props.log.length);
const pageStart = computed(() =>
	totalRows.value ? (currPage.value - 1) * pageLength.value + 1 : 0,
);
const pageEnd = computed(() => {
	const end = currPage.value * pageLength.value;
	return end > props.log.length ? props.log.length : end;
});

function capitalizeFirstLetter(string) {
	if (!string) return '';
	return string.charAt(0).toUpperCase() + string.slice(1).toLowerCase();
}

function getBadgeLabel(cell) {
	return capitalizeFirstLetter(getValueFromCell(cell));
}

function getValueFromCell(cell) {
	return cell.row.original[cell.column.columnDef.accessorKey];
}

function handleExpand(row) {
	const toggleExpandedHandler = row.getToggleExpandedHandler();
	if (row.getCanExpand()) toggleExpandedHandler();
}
</script>
