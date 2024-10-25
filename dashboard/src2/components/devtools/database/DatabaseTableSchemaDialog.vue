<template>
	<Dialog
		:options="{
			title: 'Browse Schema',
			size: '2xl'
		}"
	>
		<template #body-content>
			<p class="mb-2 text-sm text-gray-700">Select Table</p>
			<div class="flex flex-row gap-2">
				<FormControl
					class="w-full"
					type="autocomplete"
					:options="autocompleteOptions"
					v-model="selectedSchema"
				/>
				<Button
					icon="copy"
					@click="copyTableNameToClipboard"
					v-if="selectedSchema"
				/>
			</div>
			<div class="mt-3 flex flex-row gap-2" v-if="selectedSchema">
				<Button
					iconLeft="play"
					class="grow"
					variant="outline"
					@click="viewTop100Rows"
					>View Top 100 Rows</Button
				>
				<Button
					iconLeft="play"
					class="grow"
					variant="outline"
					@click="viewLast100Rows"
					>View Last 100 Rows</Button
				>
				<Button
					iconLeft="play"
					class="grow"
					variant="outline"
					@click="viewAllRows"
					>View All Rows</Button
				>
			</div>
			<ObjectList :options="listOptions" v-if="selectedSchema" />
		</template>
	</Dialog>
</template>
<script>
import { h } from 'vue';
import { FormControl } from 'frappe-ui';
import ObjectList from '../../ObjectList.vue';
import { toast } from 'vue-sonner';

export default {
	name: 'DatabaseTableSchemaDialog',
	props: ['site', 'tableSchemas'],
	emits: ['runSQLQuery'],
	components: {
		FormControl,
		ObjectList
	},
	data() {
		return {
			selectedSchema: null
		};
	},
	computed: {
		autocompleteOptions() {
			return Object.keys(this.tableSchemas).map(x => ({
				label: x,
				value: x
			}));
		},
		listOptions() {
			if (!this.selectedSchema || !this.selectedSchema.value) return {};
			return {
				data: () => {
					return this.tableSchemas[this.selectedSchema.value] ?? [];
				},
				hideControls: true,
				columns: [
					{
						label: 'Column',
						fieldname: 'column',
						width: 0.5,
						type: 'Component',
						component({ row }) {
							return h(
								'div',
								{
									class: 'truncate text-base cursor-copy',
									onClick() {
										if ('clipboard' in navigator) {
											navigator.clipboard.writeText(row.column);
											toast.success('Copied to clipboard');
										}
									}
								},
								[row.column]
							);
						}
					},
					{
						label: 'Data Type',
						fieldname: 'data_type',
						width: 0.2,
						align: 'center'
					},
					{
						label: 'Default',
						fieldname: 'default',
						width: 0.3,
						align: 'center'
					},
					{
						label: 'Nullable',
						fieldname: 'is_nullable',
						width: 0.15,
						type: 'Icon',
						Icon(value) {
							return value ? 'check' : 'x';
						},
						align: 'center'
					},

					{
						label: 'Is Indexed',
						fieldname: 'indexes',
						width: 0.15,
						align: 'center',
						type: 'Icon',
						Icon(value) {
							return value.length > 0 ? 'check' : 'x';
						}
					}
				]
			};
		}
	},
	methods: {
		copyTableNameToClipboard() {
			if ('clipboard' in navigator) {
				navigator.clipboard.writeText(this.selectedSchema.value);
				toast.success('Copied to clipboard');
			}
		},
		viewTop100Rows() {
			this.$emit(
				'runSQLQuery',
				`SELECT * FROM \`${this.selectedSchema.value}\` LIMIT 100;`
			);
		},
		viewLast100Rows() {
			this.$emit(
				'runSQLQuery',
				`SELECT * FROM \`${this.selectedSchema.value}\` ORDER BY name DESC LIMIT 100;`
			);
		},
		viewAllRows() {
			this.$emit(
				'runSQLQuery',
				`SELECT * FROM \`${this.selectedSchema.value}\`;`
			);
		}
	}
};
</script>
