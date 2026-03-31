<template>
	<Dialog
		:options="{
			title: 'Binlog Index Status',
			size: '2xl',
		}"
		v-model="show"
		@close="hide"
	>
		<template #body-content>
			<div
				v-if="$resources?.binlogs?.loading"
				class="flex w-full items-center justify-center gap-2 py-32 text-gray-700"
			>
				<Spinner class="w-4" /> Loading
			</div>
			<div v-else>
				<ObjectList
					:options="binlogsOptions"
					ref="list"
					@update:selections="handleSelection"
				/>
				<div
					class="flex items-center justify-between py-3"
					v-if="totalBinlogs > 0"
				>
					<div class="flex flex-shrink-0 items-center gap-2">
						<select class="form-select block text-sm" v-model="pageSize">
							<option :value="10">
								10&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
							</option>
							<option :value="20">
								50&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
							</option>
							<option :value="50">
								100&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
							</option>
						</select>
						<p class="text-sm text-gray-600">Per Page</p>
					</div>
					<div class="flex flex-shrink-0 items-center gap-2">
						<p class="tnum text-sm text-gray-600">
							{{ pageStart }} - {{ pageEnd }} of {{ totalBinlogs }} binlogs
						</p>
						<div class="flex gap-2">
							<Button
								variant="ghost"
								@click="goToPreviousPage()"
								:disabled="!hasPreviousPage"
								iconLeft="arrow-left"
							>
								Prev
							</Button>
							<Button
								variant="ghost"
								@click="goToNextPage()"
								:disabled="!hasNextPage"
								iconRight="arrow-right"
							>
								Next
							</Button>
						</div>
					</div>
				</div>

				<AlertBanner
					v-if="selectedBinlogs.length > 0"
					class="mt-2 mb-2"
					title="Indexing a large number of files at once can momentarily increase database load. We recommend indexing no more than 500 MB per batch."
					type="warning"
					:show-icon="false"
				/>

				<ErrorMessage
					:message="$resources.indexBinlogs.error"
					v-if="$resources.indexBinlogs.error"
					class="pt-2 pb-3"
				/>

				<!-- Index button -->
				<Button
					class="w-full"
					variant="solid"
					:disabled="selectedBinlogs.length === 0"
					@click.prevent="$resources?.indexBinlogs?.submit()"
					:loading="$resources?.indexBinlogs?.loading"
				>
					Index Binlogs
				</Button>
			</div>
		</template>
	</Dialog>
</template>
<script>
import { Dialog } from 'frappe-ui';
import { date } from '../../../utils/format';

export default {
	name: 'BinlogBrowserIndexStatusDialog',
	props: ['database_server', 'server'],
	emits: ['close', 'update:modelValue'],
	components: { Dialog },
	data() {
		return {
			page: 1,
			pageSize: 10,
			selectedBinlogs: [],
		};
	},
	mounted() {
		this.fetchBinlogStatus();
	},
	watch: {
		pageSize() {
			this.page = 1;
		},
	},
	resources: {
		binlogs() {
			if (!this.database_server) {
				return;
			}
			return {
				url: 'press.api.client.run_doc_method',
				makeParams() {
					return {
						dt: 'Database Server',
						dn: this.database_server,
						method: 'get_binlogs_indexing_status',
					};
				},
				onSuccess: (data) => {
					if (data?.message) {
						// reset selections
						this.page = 1;
						this.selectedBinlogs = [];
					}
				},
				initialData: [],
				auto: false,
			};
		},
		indexBinlogs() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams: () => {
					return {
						dt: 'Database Server',
						dn: this.database_server,
						method: 'index_binlogs_on_demand',
						args: {
							binlog_file_names: this.selectedBinlogs,
						},
					};
				},
				onSuccess: (data) => {
					if (data?.message) {
						this.hide();
						let url = `/dashboard/servers/${this.server}/jobs/${data.message}`;
						window.open(url, '_blank');
					}
				},
				initialData: [],
				auto: false,
			};
		},
	},
	computed: {
		binlogs() {
			return this.$resources?.binlogs?.data?.message || [];
		},
		binlogsOptions() {
			return {
				data: () => this.paginatedBinlogs,
				columns: [
					{
						label: 'Name',
						fieldname: 'name',
					},
					{
						label: 'Size',
						fieldname: 'size_mb',
						class: 'text-gray-600',
						format(value) {
							return value ? `${value} MB` : '';
						},
					},
					{
						label: 'Indexed',
						fieldname: 'indexed',
						width: 0.25,
						type: 'Icon',
						Icon(value) {
							return value ? 'check' : '';
						},
					},
					{
						label: 'Timestamp',
						fieldname: 'file_modification_time',
						align: 'right',
						format(value) {
							return value ? date(value, 'lll') : '';
						},
					},
				],
				selectable: true,
				showTooltip: false,
				emptyState: {
					title: 'No binlogs found',
					description: 'Database server has no binlogs',
				},
				actions: () => [
					{
						label: 'Refresh',
						icon: 'refresh-ccw',
						loading: this.$resources?.binlogs?.loading,
						onClick: () => this.fetchBinlogStatus(),
					},
				],
			};
		},
		pageStart() {
			return (this.page - 1) * this.pageSize + 1;
		},
		pageEnd() {
			return Math.min(this.page * this.pageSize, this.totalBinlogs);
		},
		totalBinlogs() {
			return this.binlogs.length;
		},
		hasPreviousPage() {
			return this.page > 1;
		},
		hasNextPage() {
			return this.page * this.pageSize < this.binlogs.length;
		},
		paginatedBinlogs() {
			const start = (this.page - 1) * this.pageSize;
			const end = start + this.pageSize;
			return this.binlogs.slice(start, end);
		},
	},
	methods: {
		fetchBinlogStatus() {
			this.$resources?.binlogs?.submit();
		},
		goToNextPage() {
			if (this.hasNextPage) {
				this.page += 1;
			}
		},
		goToPreviousPage() {
			if (this.hasPreviousPage) {
				this.page -= 1;
			}
		},
		handleSelection(selections) {
			this.selectedBinlogs = [...selections];
		},
		hide() {
			this.show = false;
			this.$emit('update:modelValue', false);
			this.$emit('close');
		},
	},
};
</script>
