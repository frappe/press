<script setup>
import {
	FlexRender,
	getCoreRowModel,
	getPaginationRowModel,
	useVueTable
} from '@tanstack/vue-table';
import { computed, ref } from 'vue';
import { unparse } from 'papaparse';

const props = defineProps({
	columns: { type: Array, required: true },
	data: { type: Array, required: true }
});

const generateData = computed(() => {
	let data = [];
	for (let i = 0; i < props.data.length; i++) {
		let row = {};
		for (let j = 0; j < props.data[i].length; j++) {
			row[props.columns[j]] = props.data[i][j];
		}
		data.push(row);
	}
	return data;
});

const table = useVueTable({
	data: generateData,
	get columns() {
		if (!props.columns?.length) return [];
		const indexColumn = {
			id: '__index',
			header: '#',
			accessorKey: '__index',
			cell: props => props.row.index + 1
		};
		const cols = props.columns.map(column => {
			return {
				id: column,
				header: column,
				accessorKey: column,
				enableSorting: false,
				isNumber: false
			};
		});
		return [indexColumn, ...cols];
	},
	initialState: {
		pagination: {
			pageSize: 10,
			pageIndex: 0
		}
	},
	filterFns: {},
	getCoreRowModel: getCoreRowModel(),
	getPaginationRowModel: getPaginationRowModel()
});

const pageLength = computed(() => table.getState().pagination.pageSize);
const currPage = computed(() => table.getState().pagination.pageIndex + 1);

const pageStart = computed(() => (currPage.value - 1) * pageLength.value + 1);
const pageEnd = computed(() => {
	const end = currPage.value * pageLength.value;
	return end > props.data.length ? props.data.length : end;
});
const totalRows = computed(() => props.data.length);
const showPagination = computed(
	() => props.data?.length && totalRows.value > pageLength.value
);

const downloadCSV = async () => {
	let csv = unparse({
		fields: props.columns,
		data: props.data
	});
	csv = '\uFEFF' + csv; // for utf-8
	// create a blob and trigger a download
	const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
	const randomId = Math.random().toString(36).substring(2, 10);
	const filename = `${randomId}.csv`;
	const link = document.createElement('a');
	link.href = URL.createObjectURL(blob);
	link.download = filename;
	link.click();
	URL.revokeObjectURL(link.href);
};
</script>

<template>
	<div class="flex h-full w-full flex-col overflow-hidden rounded border">
		<div class="relative flex flex-1 flex-col overflow-auto text-base">
			<table
				v-if="props?.columns?.length || props.data?.length"
				class="border-separate border-spacing-0"
			>
				<thead class="sticky top-0 bg-gray-50">
					<tr
						v-for="headerGroup in table.getHeaderGroups()"
						:key="headerGroup.id"
					>
						<td
							v-for="header in headerGroup.headers"
							:key="header.id"
							:colSpan="header.colSpan"
							class="border-b border-r text-gray-800"
							:width="header.column.columnDef.id === 'index' ? '6rem' : 'auto'"
						>
							<div class="flex items-center gap-2 truncate px-3 py-2">
								<FlexRender
									v-if="!header.isPlaceholder"
									:render="header.column.columnDef.header"
									:props="header.getContext()"
								/>
							</div>
						</td>
					</tr>
				</thead>
				<tbody>
					<tr v-for="(row, index) in table.getRowModel().rows" :key="row.id">
						<td
							v-for="cell in row.getVisibleCells()"
							:key="cell.id"
							class="truncate border-b border-r px-3 py-2"
							:class="[
								cell.column.columnDef.id !== 'index' ? 'min-w-[6rem] ' : ''
							]"
						>
							<FlexRender
								:render="cell.column.columnDef.cell"
								:props="cell.getContext()"
							/>
						</td>
					</tr>
					<tr height="99%" class="border-b"></tr>
				</tbody>
			</table>
			<div
				v-if="props.data?.length == 0"
				class="flex min-h-[20vh] items-center justify-center"
			>
				<div>No results to display</div>
			</div>
		</div>

		<div class="flex justify-between p-1" v-if="props.data?.length != 0">
			<Button @click="downloadCSV" iconLeft="download" variant="ghost"
				>Download as CSV</Button
			>
			<div
				v-if="showPagination"
				class="flex flex-shrink-0 items-center justify-end gap-3"
			>
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
</template>
