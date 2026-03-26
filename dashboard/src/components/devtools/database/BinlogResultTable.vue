<script setup>
import {
	FlexRender,
	getCoreRowModel,
	getPaginationRowModel,
	useVueTable,
} from '@tanstack/vue-table';
import { computed, ref, watch, reactive, onMounted } from 'vue';
import { unparse } from 'papaparse';
import MaximizedIcon from '~icons/lucide/maximize-2';

const props = defineProps({
	loadingData: { type: Boolean, default: false },
	columns: { type: Array, required: true },
	data: { type: Array, required: true },
	noOfRows: { type: Number, required: true },
	loadData: { type: Function, required: true },
	alignColumns: { type: Object, default: {} },
	cellFormatters: { type: Object, default: {} }, // For cell level formatters
	fullViewFormatters: { type: Object, default: {} }, // For full view formatters
	borderLess: { type: Boolean, default: false },
	actionHeaderLabel: { type: String },
	actionComponent: { type: Object },
	actionComponentProps: { type: Object, default: {} },
	isTruncateText: { type: Boolean, default: false },
	truncateLength: { type: Number, default: 70 },
});

const generatedData = computed(() => {
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

const paginationInfo = reactive({
	pageSize: 10,
	pageIndex: 0,
});

const loadInitialData = () => {
	const start = paginationInfo.pageIndex * paginationInfo.pageSize;
	props.loadData(start, start + paginationInfo.pageSize);
};

const table = useVueTable({
	data: generatedData,
	manualPagination: true,
	onPaginationChange: (updater) => {
		const data = updater(paginationInfo);
		paginationInfo.pageSize = data.pageSize;
		paginationInfo.pageIndex = data.pageIndex;

		const start = paginationInfo.pageIndex * paginationInfo.pageSize;
		props.loadData(start, start + paginationInfo.pageSize);
	},
	get columns() {
		if (!props.columns?.length) return [];
		const indexColumn = {
			id: '__id',
			header: '#',
			accessorKey: '__id',
			cell: (props) =>
				paginationInfo.pageSize * paginationInfo.pageIndex +
				props.row.index +
				1,
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
				enableSorting: false,
				isNumber: false,
				meta: {
					align: props.alignColumns[column] || 'left',
				},
			};
		});
		return [indexColumn, ...cols];
	},
	initialState: {
		pagination: paginationInfo.value,
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
	const fullText = cell.getValue();
	fullViewDialogHeader.value = cell.column.columnDef.header;
	fullViewDialogBody.value = fullText;
	if (props.fullViewFormatters[cell.column.columnDef.id]) {
		fullViewDialogBody.value =
			props.fullViewFormatters[cell.column.columnDef.id](fullText);
	}
	showFullViewDialog.value = true;
};

// Pagination Related Metadata
const totalRows = computed(() => props.noOfRows);
const pageLength = computed(() => paginationInfo.pageSize);
const currPage = computed(() => paginationInfo.pageIndex + 1);

const showPagination = computed(() => totalRows.value > pageLength.value);

const pageStart = computed(() => (currPage.value - 1) * pageLength.value + 1);
const pageEnd = computed(() => {
	const end = currPage.value * pageLength.value;
	return end > totalRows ? totalRows : end;
});

const isPreviousPageAvailable = computed(() => {
	return paginationInfo.pageIndex > 0;
});

const isNextPageAvailable = computed(() => {
	return (
		paginationInfo.pageIndex < Math.ceil(totalRows.value / pageLength.value) - 1
	);
});

const pageSizeRef = ref(10);
watch(
	pageSizeRef,
	(newValue) => {
		paginationInfo.pageSize = parseInt(newValue);
		paginationInfo.pageIndex = 0;
		loadInitialData();
	},
	{ immediate: true },
);
</script>

<template>
	<!-- Full Value -->
	<Dialog
		:options="{
			title: fullViewDialogHeader,
			size: '3xl',
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
			<div
				v-if="loadingData"
				class="absolute bottom-0 left-0 right-0 top-0 flex w-full items-center justify-center gap-2 bg-white text-base text-gray-800 min-h-80"
			>
				<Spinner class="w-4" /> Crunching data...
			</div>
			<div
				v-if="props.data?.length == 0"
				class="flex flex-col h-80 items-center justify-center text-gray-800 text-base gap-1"
			>
				<p>No results to display</p>
				<br />
				<p>Try adjusting your search criteria or filters</p>
			</div>
			<table
				v-else
				class="border-separate border-spacing-0"
				:class="{
					'h-80': !props.data?.length,
				}"
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
							class="border-b border-r text-gray-800"
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
							class="truncate border-r px-3 py-2"
							:class="{
								'border-b': !(
									index === table.getRowModel().rows.length - 1 && borderLess
								),
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
		</div>

		<div
			class="flex flex-shrink-0 items-center justify-between px-1 py-1"
			v-if="props.data?.length != 0 && showPagination"
		>
			<div class="flex flex-shrink-0 items-center gap-2">
				<select
					class="form-select block text-sm"
					v-model="pageSizeRef"
					:disabled="loadingData"
				>
					<option value="10">10&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</option>
					<option value="25">25&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</option>
					<option value="50">50&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</option>
				</select>
				<p class="text-sm text-gray-600">Per Page</p>
			</div>

			<div class="flex flex-shrink-0 items-center gap-2">
				<p class="tnum text-sm text-gray-600">
					{{ pageStart }} - {{ pageEnd }} of {{ totalRows }} rows
				</p>
				<div class="flex gap-2">
					<Button
						variant="ghost"
						@click="table.previousPage()"
						:disabled="!isPreviousPageAvailable || loadingData"
						iconLeft="arrow-left"
					>
						Prev
					</Button>
					<Button
						variant="ghost"
						@click="table.nextPage()"
						:disabled="!isNextPageAvailable || loadingData"
						iconRight="arrow-right"
					>
						Next
					</Button>
				</div>
			</div>
		</div>
	</div>
</template>
