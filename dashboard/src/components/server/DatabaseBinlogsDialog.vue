<template>
	<Dialog
		:options="{
			title: 'Database Binlogs',
			size: '2xl',
		}"
		v-model="show"
	>
		<template #body-content>
			<div
				v-if="$resources.binlogs.loading"
				class="flex w-full items-center justify-center gap-2 py-32 text-gray-700"
			>
				<Spinner class="w-4" /> Loading
			</div>
			<div v-else>
				<ObjectList
					:options="binlogsOptions"
					@update:selections="handleSelection"
					ref="list"
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
					v-if="totalBinlogs > 0"
					title="To purge binlogs, select the oldest binlog you want to delete. It and all earlier binlogs will be removed."
					type="info"
					:showIcon="false"
				>
				</AlertBanner>
			</div>
		</template>
	</Dialog>
</template>
<script>
import { toast } from 'vue-sonner';
import { confirmDialog } from '../../utils/components';
import { bytes, date } from '../../utils/format';
import ObjectList from '../ObjectList.vue';
import { getToastErrorMessage } from '../../utils/toast';

export default {
	name: 'DatabaseBinlogsDialog',
	props: {
		databaseServer: {
			type: String,
			required: true,
		},
	},
	components: { ObjectList },
	emits: ['update:show'],
	data() {
		return {
			show: true,
			page: 1,
			pageSize: 10,
			lastPurgeFrom: null,
			purgeFrom: null,
			selectingOtherRows: false,
			previousSelections: new Set(),
		};
	},
	resources: {
		binlogs() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				makeParams: () => {
					return {
						dt: 'Database Server',
						dn: this.databaseServer,
						method: 'get_binlogs_info',
						args: {},
					};
				},
				onSuccess: (data) => {
					if (data?.message) {
						// reset selections
						this.page = 1;
						this.purgeFrom = null;
						this.lastPurgeFrom = null;
						this.previousSelections = new Set();
						this.selectingOtherRows = false;
					}
				},
				initialData: [],
				auto: true,
			};
		},
		purgeBinlogs() {
			if (!this.purgeFrom) return;

			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				makeParams: () => {
					return {
						dt: 'Database Server',
						dn: this.databaseServer,
						method: 'purge_binlogs',
						args: {
							to_binlog: this.purgeFrom,
						},
					};
				},
				auto: false,
			};
		},
	},
	computed: {
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
		binlogs() {
			return this.$resources?.binlogs?.data?.message || [];
		},
		sortedBinlogNames() {
			return this.binlogs.map((b) => b.name).sort();
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
						fieldname: 'size',
						class: 'text-gray-600',
						format(value) {
							return bytes(value);
						},
					},
					{
						label: 'Timestamp',
						fieldname: 'modified_at',
						align: 'right',
						format(value) {
							return value ? date(value, 'lll') : '';
						},
					},
				],
				showTooltip: false,
				selectable: true,
				emptyState: {
					title: 'No binlogs found',
					description: 'Your database server has no binlogs',
				},
				actions: () => [
					{
						iconLeft: 'trash-2',
						theme: 'red',
						variant: 'solid',
						label: 'Remove Binlogs',
						disabled: !this.purgeFrom,
						onClick: () => {
							this.closeDialog();
							confirmDialog({
								title: 'Remove Binlogs',
								message: `Are you sure you want to remove binlogs from <b>${this.purgeFrom} (${this.purgeFromDate})</b> and all older ones?\nThis action cannot be undone.`,
								primaryAction: {
									label: 'Confirm & Remove',
									variant: 'solid',
									theme: 'red',
									onClick: ({ hide }) => {
										if (this.$resources.purgeBinlogs.loading) {
											return;
										}
										const purgeFrom = this.purgeFrom;
										const purgeFromDate = this.purgeFromDate;
										return toast.promise(
											this.$resources.purgeBinlogs.submit(),
											{
												loading: 'Purging binlogs...',
												success: () => {
													hide();
													return `Binlogs from ${purgeFrom} (${purgeFromDate}) have been removed`;
												},
												error: (e) => getToastErrorMessage(e),
											},
										);
									},
								},
							});
						},
					},
					{
						label: 'Refresh',
						icon: 'refresh-ccw',
						loading: this.$resources.binlogs.loading,
						onClick: () => this.$resources.binlogs.reload(),
					},
				],
			};
		},
		purgeFromDate() {
			if (!this.purgeFrom) return null;
			const binlog = this.binlogs.find((b) => b.name === this.purgeFrom);
			return binlog ? date(binlog.modified_at, 'lll') : '---';
		},
	},
	methods: {
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
			if (this.selectingOtherRows) {
				console.log('Currently selecting other rows, ignoring selection event');
				return;
			}

			const sortedSelections = Array.from(selections).sort().reverse();
			if (sortedSelections.length == 0) {
				this.purgeFrom = null;
				this.selectingOtherRows = false;
				return;
			}

			this.selectingOtherRows = true;
			const reversedSortedBinlogNames = [...this.sortedBinlogNames].reverse();

			this.purgeFrom = sortedSelections[0];
			if (!this.purgeFrom) {
				return;
			}

			setTimeout(() => {
				if (this.lastPurgeFrom && this.purgeFrom === this.lastPurgeFrom) {
					// reverse the user action
					const unselectedBinlog = this.findFirstMissingAndNextAvailable(
						sortedSelections,
						reversedSortedBinlogNames,
					).firstMissing;
					if (unselectedBinlog) {
						this.$refs.list.toggleRowSelection(unselectedBinlog);
						console.log('Reversing selection to', unselectedBinlog);
					}
				} else {
					// find index of purgeFrom in sorted binlog names
					const purgeIndex = reversedSortedBinlogNames.indexOf(this.purgeFrom);
					for (let i = 0; i < reversedSortedBinlogNames.length; i++) {
						const binlog = reversedSortedBinlogNames[i];
						if (i < purgeIndex && selections.has(binlog)) {
							// console.log("Trying to deselect", binlog);
							this.$refs.list.toggleRowSelection(binlog);
						}
						if (i >= purgeIndex && !selections.has(binlog)) {
							// console.log("Trying to select", binlog);
							this.$refs.list.toggleRowSelection(binlog);
						}
					}

					this.lastPurgeFrom = this.purgeFrom;
					this.previousSelections = new Set(sortedSelections);
				}
				this.selectingOtherRows = false;
			}, 150);
		},
		findFirstMissingAndNextAvailable(selections, fullList) {
			const selectionSet = new Set(selections);
			const startIdx = fullList.indexOf(selections[0]);

			let firstMissing = null;
			let nextAvailable = null;

			for (let i = startIdx; i < fullList.length; i++) {
				const binlog = fullList[i];

				if (!selectionSet.has(binlog)) {
					firstMissing = binlog;

					// find next available selection *after* this missing one
					for (let j = i + 1; j < fullList.length; j++) {
						if (selectionSet.has(fullList[j])) {
							nextAvailable = fullList[j];
							break;
						}
					}
					break;
				}
			}

			if (nextAvailable === null && selections.length > 0) {
				nextAvailable = selections[0];
			}

			return { firstMissing, nextAvailable };
		},
		showDialog() {
			this.show = true;
			this.$emit('update:show', true);
		},
		closeDialog() {
			this.show = false;
			this.$emit('update:show', false);
		},
	},
};
</script>
