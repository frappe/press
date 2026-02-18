<script setup>
import {
	FlexRender,
	getCoreRowModel,
	getPaginationRowModel,
	useVueTable,
} from '@tanstack/vue-table';
import { computed, ref, watch } from 'vue';
import { unparse } from 'papaparse';
import MaximizedIcon from '~icons/lucide/maximize-2';

const props = defineProps({
	columns: { type: Array, required: true },
	data: { type: Array, required: true },
	alignColumns: { type: Object, default: {} },
	cellFormatters: { type: Object, default: {} }, // For cell level formatters
	fullViewFormatters: { type: Object, default: {} }, // For full view formatters
	borderLess: { type: Boolean, default: false },
	enableCSVExport: { type: Boolean, default: true },
	actionHeaderLabel: { type: String },
	actionComponent: { type: Object },
	actionComponentProps: { type: Object, default: {} },
	isTruncateText: { type: Boolean, default: false },
	truncateLength: { type: Number, default: 70 },
	hideIndexColumn: { type: Boolean, default: false },
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

const lastColumn =
	props.columns.length > 0 ? props.columns[props.columns.length - 1] : '';

const table = useVueTable({
	data: generateData,
	get columns() {
		if (!props.columns?.length) return [];
		const indexColumn = {
			id: '__index',
			header: '#',
			accessorKey: '__index',
			cell: (props) => props.row.index + 1,
		};
		const cols = props.columns.map((column) => {
			return {
				id: column,
				cell: (cellProps) => {
					const value = cellProps.getValue();
					if (props.isTruncateText) {
						if (
							value &&
							typeof value === 'string' &&
							value.length > props.truncateLength
						) {
							return `${value.substring(0, props.truncateLength)}`;
						}
					}
					if (props.cellFormatters[cellProps.column.columnDef.id]) {
						return props.cellFormatters[cellProps.column.columnDef.id](value);
					}
					return value;
				},
				header: column,
				accessorKey: column,
				accessorFn: (row) => row[column],
				enableSorting: false,
				isNumber: false,
				meta: {
					align: props.alignColumns[column] || 'left',
				},
			};
		});
		if (props.hideIndexColumn) {
			return cols;
		}
		return [indexColumn, ...cols];
	},
	initialState: {
		pagination: {
			pageSize: 10,
			pageIndex: 0,
		},
	},
	filterFns: {},
	getCoreRowModel: getCoreRowModel(),
	getPaginationRowModel: getPaginationRowModel(),
});

const isTextTruncated = (cell) => {
	const value = cell.getValue();
	return (
		props.isTruncateText &&
		value &&
		typeof value === 'string' &&
		value.length > props.truncateLength
	);
};

const fullViewDialogHeader = ref(null);
const fullViewDialogBody = ref(null);
const showFullViewDialog = ref(false);
const handleViewFull = (cell) => {
	// Avoid using cell.getValue(), as that reset state of pagination
	const fullText = cell.getContext().row.original[cell.column.columnDef.header];
	fullViewDialogHeader.value = cell.column.columnDef.header;
	fullViewDialogBody.value = fullText;
	if (props.fullViewFormatters[cell.column.columnDef.id]) {
		fullViewDialogBody.value =
			props.fullViewFormatters[cell.column.columnDef.id](fullText);
	}
	showFullViewDialog.value = true;
};

const pageLength = computed(() => table.getState().pagination.pageSize);
const currPage = computed(() => table.getState().pagination.pageIndex + 1);

const pageStart = computed(() => (currPage.value - 1) * pageLength.value + 1);
const pageEnd = computed(() => {
	const end = currPage.value * pageLength.value;
	return end > props.data.length ? props.data.length : end;
});
const totalRows = computed(() => props.data.length);
const showPagination = computed(
	() => props.data?.length && totalRows.value > pageLength.value,
);

const pageSize = ref(10);
watch(pageSize, () => {
	currPage.value = 1;
	table.setPageSize(pageSize.value);
});

const downloadCSV = async () => {
	let csv = unparse({
		fields: props.columns,
		data: props.data,
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
	<!-- Full Value -->
	<Dialog
		:options="{
			title: fullViewDialogHeader,
			size: '2xl',
		}"
		v-model="showFullViewDialog"
	>
		<template #body-content>
			<pre
				class="mt-2 whitespace-pre-wrap rounded-lg border-2 border-gray-200 bg-gray-100 p-3 text-sm text-gray-700"
				>{{ fullViewDialogBody }}</pre
			>
		</template>
	</Dialog>
	<!-- Table -->
	<div
		class="flex h-full w-full flex-col overflow-hidden"
		:class="{
			'rounded border': !borderLess,
		}"
	>
		<div class="relative flex flex-1 flex-col overflow-auto text-base">
			<table
				v-if="props?.columns?.length || props.data?.length"
				class="border-separate border-spacing-0"
			>
				<thead class="sticky top-0 z-10 bg-gray-50">
					<tr
						v-for="headerGroup in table.getHeaderGroups()"
						:key="headerGroup.id"
					>
						<td
							v-for="header in headerGroup.headers"
							:key="header.id"
							:colSpan="header.colSpan"
							class="border-b text-gray-800"
							:class="{
								'border-r': header.column.columnDef.id !== lastColumn,
							}"
							:width="
								header.column.columnDef.id === '__index' ? '6rem' : 'auto'
							"
						>
							<div class="flex items-center gap-2 truncate px-3 py-2">
								<FlexRender
									v-if="!header.isPlaceholder"
									:render="header.column.columnDef.header"
									:props="header.getContext()"
								/>
							</div>
						</td>
						<td
							class="w-[10rem] border-b border-r text-center text-gray-800"
							v-if="actionHeaderLabel"
						>
							{{ actionHeaderLabel }}
						</td>
					</tr>
				</thead>
				<tbody>
					<tr v-for="(row, index) in table.getRowModel().rows" :key="row.id">
						<td
							v-for="cell in row.getVisibleCells()"
							:key="cell.id"
							:align="cell.column.columnDef.meta?.align"
							class="truncate px-3 py-2"
							:class="{
								'border-b': !(
									index === table.getRowModel().rows.length - 1 && borderLess
								),
								'border-r': cell.column.columnDef.id !== lastColumn,
								'min-w-[6rem] ': cell.column.columnDef.id !== 'index',
							}"
						>
							<FlexRender
								:render="cell.column.columnDef.cell"
								:props="cell.getContext()"
							/>
							<MaximizedIcon
								v-if="isTextTruncated(cell)"
								@click="handleViewFull(cell)"
								class="!my-0 ml-2 inline-block !h-4 !w-4 cursor-pointer text-gray-700"
							/>
						</td>
						<td
							class="w-[6rem] border-b border-r text-center text-gray-800"
							v-if="actionComponent"
						>
							<component
								:is="actionComponent"
								:row="row.original"
								v-bind="actionComponentProps"
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

		<div
			class="flex justify-between p-1"
			v-if="props.data?.length != 0 && (enableCSVExport || showPagination)"
		>
			<Button
				@click="downloadCSV"
				iconLeft="download"
				variant="ghost"
				v-if="enableCSVExport"
				>Download as CSV</Button
			>
			<div v-else></div>
			<!-- blank div added to prevent broken layout -->
			<div
				v-if="showPagination"
				class="flex flex-shrink-0 items-center justify-end gap-3"
			>
				<div class="flex flex-shrink-0 items-center justify-end gap-3">
					<div class="flex flex-shrink-0 items-center gap-2 border-r-2 pr-3">
						<p class="text-sm text-gray-600">Per Page</p>
						<select
							class="form-select block !py-0.5 text-sm"
							v-model="pageSize"
						>
							<option value="10">10&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</option>
							<option value="50">50&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</option>
							<option value="100">
								100&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
							</option>
							<option value="200">
								200&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
							</option>
						</select>
					</div>
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
</template>
