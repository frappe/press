<template>
	<Dialog :options="{ title: 'Add User', size: '2xl' }" v-model="showDialog">
		<template #body-content>
			<div class="flex flex-col gap-2">
				<FormControl
					type="select"
					:options="[
						{
							label: 'Read only access to all the tables',
							value: 'read_only'
						},
						{
							label: 'Read/Write access to all the tables',
							value: 'read_write'
						},
						{
							label: 'Granular access',
							value: 'granular'
						}
					]"
					size="sm"
					variant="subtle"
					:disabled="false"
					label="Access Mode"
					v-model="mode"
				/>
				<div v-if="mode == 'granular'">
					<div
						v-if="isLoadingTableSchemas"
						class="flex w-full flex-col items-center justify-center gap-2 text-base text-gray-700"
					>
						<span class="flex flex-row gap-2 py-20">
							<Spinner class="w-4" /> Fetching table schemas
						</span>
						<p class="text-sm">This can take upto 5 minutes</p>
					</div>
					<div v-else class="mt-2">
						<p class="text-sm font-semibold text-gray-600">
							Configure Permissions
						</p>
						<ObjectList :options="listOptions" />
						<div class="mb-4 mt-4 flex w-full">
							<Button variant="outline" @click="addFieldForNewPermissionEntry"
								>Add Permission</Button
							>
						</div>
					</div>
				</div>
				<Button
					class="mt-2 w-full"
					variant="solid"
					theme="gray"
					:disabled="mode == 'granular' && isLoadingTableSchemas"
					:loading="this.$resources.createDatabaseUser.loading"
					@click="this.$resources.createDatabaseUser.submit()"
				>
					Create User
				</Button>
			</div>
		</template>
	</Dialog>
</template>
<script>
import { h } from 'vue';
import ObjectList from '../ObjectList.vue';
import { FormControl } from 'frappe-ui';
import { icon } from '../../utils/components';
import { toast } from 'vue-sonner';

export default {
	name: 'SiteDatabaseAddUserDialog',
	props: ['site'],
	emits: ['update:modelValue', 'success'],
	components: {
		FormControl,
		ObjectList,
		icon
	},
	data() {
		return {
			mode: 'read_only',
			permissions: [],
			lastGenratedRowId: 0
		};
	},
	mounted() {
		this.fetchTableSchemas();
		this.addFieldForNewPermissionEntry();
	},
	resources: {
		tableSchemas() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				auto: false,
				onSuccess: data => {
					if (data?.message?.loading) {
						setTimeout(this.fetchTableSchemas, 5000);
					}
				}
			};
		},
		createDatabaseUser() {
			return {
				url: 'press.api.client.insert',
				makeParams() {
					let permissions = [];
					this.permissions.forEach(permission => {
						if (permission.table) {
							permissions.push({
								table: permission.table,
								mode: permission.mode,
								allow_all_columns: permission.columns.length == 0,
								selected_columns: permission.columns.join('\n')
							});
						}
					});
					return {
						doc: {
							doctype: 'Site Database User',
							team: this.$team.doc.name,
							site: this.site,
							mode: this.mode,
							permissions: permissions
						}
					};
				},
				onSuccess() {
					toast.success('User created successfully');
					this.$emit('success');
				}
			};
		}
	},
	computed: {
		listOptions() {
			return {
				data: () => this.permissions,
				columns: [
					{
						label: 'Table',
						fieldname: 'table',
						width: 1,
						type: 'Component',
						component: ({ row }) => {
							return h(FormControl, {
								class: 'w-full -mx-1.5',
								type: 'autocomplete',
								modelValue: row.table,
								'onUpdate:modelValue': newValue => {
									row.table = newValue?.value || '';
								},
								options: this.autocompleteTableOptions
							});
						}
					},
					{
						label: 'Mode',
						fieldname: 'mode',
						width: 0.6,
						align: 'center',
						type: 'Component',
						component: ({ row }) => {
							return h(FormControl, {
								type: 'select',
								class: 'w-full',
								options: [
									{
										label: 'Read Only',
										value: 'read_only'
									},
									{
										label: 'Read Write',
										value: 'read_write'
									}
								],
								modelValue: row.mode,
								'onUpdate:modelValue': newValue => {
									row.mode = newValue;
									this.addFieldForNewPermissionEntry();
								}
							});
						}
					},
					{
						label: 'Columns',
						width: 0.8,
						fieldname: 'columns',
						align: 'center'
					},
					{
						label: '',
						width: 0.2,
						align: 'right',
						type: 'Button',
						Button: ({ row }) => {
							return {
								label: true ? 'check' : 'plus',
								slots: {
									icon: icon('minus')
								},
								variant: 'subtle',
								onClick: event => {
									this.removePermissionEntry(row.name);
									event.stopPropagation();
								}
							};
						}
					}
				]
			};
		},
		showDialog: {
			get() {
				return this.modelValue;
			},
			set(value) {
				this.$emit('update:modelValue', value);
			}
		},
		isLoadingTableSchemas() {
			if (this.$resources?.tableSchemas?.loading) return true;
			if (this.$resources?.tableSchemas?.data?.message?.loading) return true;
			return false;
		},
		tableNames() {
			if (this.isLoadingTableSchemas) return [];
			if (!this.$resources?.tableSchemas?.data?.message?.data) return [];
			return Object.keys(this.$resources?.tableSchemas?.data?.message?.data);
		},
		autocompleteTableOptions() {
			if (this.isLoadingTableSchemas) return [];
			if (!this.$resources?.tableSchemas?.data?.message?.data) return [];
			return Object.keys(
				this.$resources?.tableSchemas?.data?.message?.data
			).map(x => ({
				label: x,
				value: x
			}));
		}
	},
	methods: {
		fetchTableSchemas(reload = false) {
			if (!this.site) return;
			this.$resources.tableSchemas.submit({
				dt: 'Site',
				dn: this.site,
				method: 'fetch_database_table_schema',
				args: {
					reload
				}
			});
		},
		getColumns(table) {
			if (this.isLoadingTableSchemas) return [];
			if (!this.$resources?.tableSchemas?.data?.message?.data) return [];
			return Object.keys(
				this.$resources?.tableSchemas?.data?.message?.data[table].map(
					x => x.column
				)
			);
		},
		addFieldForNewPermissionEntry() {
			this.lastGenratedRowId = this.lastGenratedRowId + 1;
			this.permissions = [
				...this.permissions,
				{
					name: String(this.lastGenratedRowId),
					table: '',
					mode: 'read_only',
					columns: []
				}
			];
		},
		removePermissionEntry(name) {
			this.permissions = this.permissions.filter(x => x.name !== name);
		}
	}
};
</script>
