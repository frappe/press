<template>
	<Dialog
		:options="{
			title: isEditMode ? 'Edit Database User' : 'Add Database User',
			size: '2xl',
		}"
		v-model="showDialog"
	>
		<template #body-content>
			<div class="flex flex-col gap-2">
				<AlertBanner
					v-if="
						isEditMode &&
						this.$resources?.databaseUser?.doc?.status === 'Failed' &&
						this.$resources?.databaseUser?.doc?.failure_reason
					"
					:title="this.$resources?.databaseUser?.doc?.failure_reason"
					type="error"
				>
				</AlertBanner>
				<FormControl
					class="mt-2"
					type="text"
					size="sm"
					variant="subtle"
					label="Label (to identify the user)"
					v-model="label"
				/>
				<FormControl
					type="select"
					:options="[
						{
							label: 'Read only access to all the tables',
							value: 'read_only',
						},
						{
							label: 'Read/Write access to all the tables',
							value: 'read_write',
						},
						{
							label: 'Granular access',
							value: 'granular',
						},
					]"
					size="sm"
					variant="subtle"
					:disabled="false"
					label="Access Mode"
					v-model="mode"
				/>
				<FormControl
					v-if="!isEditMode"
					class="mt-2"
					type="number"
					size="sm"
					variant="subtle"
					label="Database Connections"
					v-model="database_connections"
				/>
				<!-- Permission configuration for Granular Mode -->
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
						<p class="text-sm font-medium text-gray-600">
							Configure Permissions
						</p>
						<ObjectList :options="listOptions" />
						<div class="mt-4 flex w-full gap-2">
							<Button
								variant="outline"
								iconLeft="plus"
								@click="addNewTablePermissionEntry"
								>Add Table</Button
							>
							<Button
								variant="outline"
								iconLeft="refresh-ccw"
								:loading="isLoadingTableSchemas"
								@click="() => fetchTableSchemas(true)"
								>Refresh Schema</Button
							>
						</div>
					</div>
				</div>
			</div>
			<ErrorMessage
				:message="
					this.$resources?.createDatabaseUser?.error ||
					this.$resources?.updateDatabaseUser?.error
				"
				class="mt-2"
			/>
		</template>

		<template #actions>
			<Button
				v-if="!isEditMode"
				class="w-full"
				variant="solid"
				theme="gray"
				:disabled="mode == 'granular' && isLoadingTableSchemas"
				:loading="this.$resources.createDatabaseUser.loading"
				@click="this.$resources.createDatabaseUser.submit()"
			>
				Create User
			</Button>
			<Button
				v-else
				class="w-full"
				variant="solid"
				theme="gray"
				:disabled="mode == 'granular' && isLoadingTableSchemas"
				:loading="this.$resources.updateDatabaseUser.loading"
				@click="this.$resources.updateDatabaseUser.submit()"
				>Save Changes</Button
			>
		</template>
	</Dialog>
</template>
<script>
import { h } from 'vue';
import ObjectList from '../ObjectList.vue';
import { ErrorMessage, FormControl } from 'frappe-ui';
import { icon } from '../../utils/components';
import { toast } from 'vue-sonner';
import AlertBanner from '../AlertBanner.vue';
import SiteDatabaseColumnsSelector from './SiteDatabaseColumnsSelector.vue';
import { DashboardError } from '../../utils/error';

export default {
	name: 'SiteDatabaseAddEditUserDialog',
	props: ['site', 'db_user_name', 'modelValue'], // db_user_name is optional, only provide to edit
	emits: ['success'],
	components: {
		FormControl,
		ObjectList,
		icon,
		AlertBanner,
		SiteDatabaseColumnsSelector,
	},
	data() {
		return {
			label: '',
			mode: 'read_only',
			database_connections: 1,
			permissions: [],
			lastGeneratedRowId: 0,
		};
	},
	mounted() {
		this.fetchTableSchemas();
		if (!this.isEditMode) {
			this.addNewTablePermissionEntry();
		} else {
			this.$resources.databaseUser.reload();
		}
	},
	resources: {
		tableSchemas() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				auto: false,
				onSuccess: (data) => {
					if (data?.message?.loading) {
						setTimeout(this.fetchTableSchemas, 5000);
					}
				},
			};
		},
		databaseUser() {
			return {
				type: 'document',
				doctype: 'Site Database User',
				name: this.db_user_name,
				auto: false,
				onSuccess: (data) => {
					this.label = data?.label;
					this.mode = data?.mode;
					let fetched_permissions = (data?.permissions ?? []).map((x) => {
						return {
							...x,
							columns: x.selected_columns.split('\n').filter((x) => x),
						};
					});
					this.permissions = fetched_permissions;
					this.database_connections = data?.max_connections ?? 1;
				},
			};
		},
		createDatabaseUser() {
			return {
				url: 'press.api.client.insert',
				makeParams() {
					let permissions = [];
					this.permissions.forEach((permission) => {
						if (permission.table) {
							permissions.push({
								table: permission.table,
								mode: permission.mode,
								allow_all_columns: permission.columns.length == 0,
								selected_columns: permission.columns.join('\n'),
							});
						}
					});
					return {
						doc: {
							doctype: 'Site Database User',
							label: this.label,
							team: this.$team.doc.name,
							site: this.site,
							mode: this.mode,
							permissions: permissions,
							max_connections: parseInt(this.database_connections || 1),
						},
					};
				},
				validate() {
					if (!this.label)
						throw new DashboardError('Please provide a label for the user');
				},
				onSuccess() {
					toast.success('User created successfully');
					this.$emit('success');
				},
			};
		},
		updateDatabaseUser() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams() {
					let permissions = [];
					this.permissions.forEach((permission) => {
						if (permission.table) {
							permissions.push({
								table: permission.table,
								mode: permission.mode,
								allow_all_columns: permission.columns.length == 0,
								selected_columns: permission.columns.join('\n'),
							});
						}
					});
					return {
						dt: 'Site Database User',
						dn: this.db_user_name,
						method: 'save_and_apply_changes',
						args: {
							label: this.label,
							mode: this.mode,
							permissions: permissions,
						},
					};
				},
				validate() {
					if (!this.label)
						throw new DashboardError('Please provide a label for the user');
				},
				onSuccess() {
					toast.success('User updated successfully');
					this.$emit('success');
				},
			};
		},
	},
	computed: {
		listOptions() {
			return {
				data: () => this.permissions,
				columns: [
					{
						label: 'Table',
						fieldname: 'table',
						width: '200px',
						type: 'Component',
						component: ({ row }) => {
							return h(FormControl, {
								class: 'w-full -mx-1.5',
								type: 'autocomplete',
								modelValue: row.table,
								'onUpdate:modelValue': (newValue) => {
									row.table = newValue?.value || '';
								},
								options: this.autocompleteTableOptions,
							});
						},
					},
					{
						label: 'Mode',
						fieldname: 'mode',
						width: 1,
						align: 'center',
						type: 'Component',
						component: ({ row }) => {
							return h(FormControl, {
								type: 'select',
								class: 'w-full',
								options: [
									{
										label: 'Read Only',
										value: 'read_only',
									},
									{
										label: 'Read Write',
										value: 'read_write',
									},
								],
								modelValue: row.mode,
								'onUpdate:modelValue': (newValue) => {
									row.mode = newValue;
								},
							});
						},
					},
					{
						label: 'Columns',
						width: '200px',
						fieldname: 'columns',
						align: 'center',
						type: 'Component',
						component: ({ row }) => {
							return h(SiteDatabaseColumnsSelector, {
								modelValue: row.columns,
								availableColumns: this.getColumns(row.table),
								'onUpdate:modelValue': (newValues) => {
									row.columns = [...newValues];
								},
							});
						},
					},
					{
						label: '',
						width: 0.6,
						align: 'right',
						type: 'Button',
						Button: ({ row }) => {
							return {
								label: true ? 'check' : 'plus',
								slots: {
									icon: icon('x'),
								},
								variant: 'subtle',
								onClick: (event) => {
									this.removePermissionEntry(row.name);
									event.stopPropagation();
								},
							};
						},
					},
				],
			};
		},
		showDialog: {
			get() {
				return this.modelValue;
			},
			set(value) {
				this.$emit('update:modelValue', value);
			},
		},
		isEditMode() {
			return !!this.db_user_name;
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
				this.$resources?.tableSchemas?.data?.message?.data,
			).map((x) => ({
				label: x,
				value: x,
			}));
		},
	},
	methods: {
		fetchTableSchemas(reload = false) {
			if (!this.site) return;
			this.$resources.tableSchemas.submit({
				dt: 'Site',
				dn: this.site,
				method: 'fetch_database_table_schema',
				args: {
					reload,
				},
			});
		},
		getColumns(table) {
			if (!table) return [];
			if (this.isLoadingTableSchemas) return [];
			if (!this.$resources?.tableSchemas?.data?.message?.data) return [];
			let columnSchemas =
				this.$resources?.tableSchemas?.data?.message?.data[table]?.columns ??
				[];
			let columns = [];
			columnSchemas.forEach((x) => {
				columns.push(x.column);
			});
			return columns;
		},
		addNewTablePermissionEntry() {
			this.lastGeneratedRowId = this.lastGeneratedRowId + 1;
			this.permissions = [
				...this.permissions,
				{
					name: String(this.lastGeneratedRowId),
					table: '',
					mode: 'read_only',
					columns: [],
				},
			];
		},
		removePermissionEntry(name) {
			this.permissions = this.permissions.filter((x) => x.name !== name);
		},
	},
};
</script>
