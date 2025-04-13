<template>
	<Dialog
		:options="{
			title: 'Manage Database Users',
			size: planSupportsDatabaseAccess ? '3xl' : 'xl',
		}"
		v-model="show"
	>
		<template #body-content>
			<!-- Not available on current plan, upsell higher plans -->
			<div v-if="!planSupportsDatabaseAccess">
				<div>
					<p class="text-base">
						Database access is not available on your current plan. <br />Please
						upgrade to a higher plan to use this feature.
					</p>

					<Button
						class="mt-4 w-full"
						variant="solid"
						@click="showChangePlanDialog = true"
					>
						Upgrade Site Plan
					</Button>
					<ManageSitePlansDialog
						:site="site"
						v-model="showChangePlanDialog"
						v-if="showChangePlanDialog"
					/>
				</div>
			</div>

			<!-- Available on the current plan -->
			<div v-else>
				<ObjectList :options="listOptions" />
			</div>
		</template>
	</Dialog>

	<SiteDatabaseUserCredentialDialog
		:name="selectedUser"
		v-model="showDatabaseUserCredentialDialog"
		v-if="showDatabaseUserCredentialDialog"
	/>

	<SiteDatabaseAddEditUserDialog
		:site="site"
		:key="selectedUser ? selectedUser : 'new'"
		:db_user_name="selectedUser"
		v-model="showDatabaseAddEditUserDialog"
		v-if="showDatabaseAddEditUserDialog"
		@success="this.hideSiteDatabaseAddEditUserDialog"
	/>
</template>
<script>
import { defineAsyncComponent } from 'vue';
import { getCachedDocumentResource } from 'frappe-ui';
import ClickToCopyField from './ClickToCopyField.vue';
import ObjectList from './ObjectList.vue';
import { date } from '../utils/format';
import { confirmDialog, icon } from '../utils/components';
import SiteDatabaseUserCredentialDialog from './site_database_user/SiteDatabaseUserCredentialDialog.vue';
import SiteDatabaseAddEditUserDialog from './site_database_user/SiteDatabaseAddEditUserDialog.vue';
import { toast } from 'vue-sonner';

export default {
	name: 'SiteDatabaseAccessDialog',
	props: ['site'],
	components: {
		ManageSitePlansDialog: defineAsyncComponent(
			() => import('./ManageSitePlansDialog.vue'),
		),
		ClickToCopyField,
		ObjectList,
		SiteDatabaseUserCredentialDialog,
		SiteDatabaseAddEditUserDialog,
	},
	data() {
		return {
			mode: 'read_only',
			show: true,
			showChangePlanDialog: false,
			selectedUser: '',
			showDatabaseUserCredentialDialog: false,
			showDatabaseAddEditUserDialog: false,
		};
	},
	watch: {
		showDatabaseUserCredentialDialog(val) {
			if (!val) {
				this.show = true;
			}
		},
		showDatabaseAddEditUserDialog(val) {
			if (!val) {
				this.show = true;
			}
		},
	},
	resources: {
		deleteSiteDatabaseUser() {
			return {
				url: 'press.api.client.run_doc_method',
				onSuccess() {
					toast.success('Database User will be deleted shortly');
				},
				onError(err) {
					toast.error(
						err.messages.length
							? err.messages.join('\n')
							: 'Failed to initiate database user deletion',
					);
				},
			};
		},
	},
	computed: {
		listOptions() {
			return {
				doctype: 'Site Database User',
				filters: {
					site: this.site,
					status: ['!=', 'Archived'],
				},
				searchField: 'label',
				filterControls() {
					return [
						{
							type: 'select',
							label: 'Status',
							fieldname: 'status',
							options: ['', 'Pending', 'Active', 'Failed'],
						},
					];
				},
				columns: [
					{
						label: 'Label',
						fieldname: 'label',
						width: '150px',
					},
					{
						label: 'Status',
						fieldname: 'status',
						width: 0.5,
						align: 'center',
						type: 'Badge',
					},
					{
						label: 'DB Connections',
						fieldname: 'max_connections',
						width: 0.5,
						align: 'center',
						format: (value) => `${value} Connection` + (value > 1 ? 's' : ''),
					},
					{
						label: 'Mode',
						fieldname: 'mode',
						width: 0.5,
						align: 'center',
						format: (value, row) => {
							return {
								read_only: 'Read Only',
								read_write: 'Read/Write',
								granular: 'Granular',
							}[value];
						},
					},
					{
						label: 'Created On',
						fieldname: 'creation',
						width: 0.5,
						align: 'center',
						format: (value) => date(value, 'll'),
					},
				],
				rowActions: ({ row, listResource, documentResource }) => {
					if (row.status === 'Archived' || row.status === 'Pending') {
						return [];
					}
					return [
						{
							label: 'View Credential',
							onClick: () => {
								this.show = false;
								this.selectedUser = row.name;
								this.showDatabaseUserCredentialDialog = true;
							},
						},
						{
							label: 'Configure User',
							onClick: () => {
								this.selectedUser = row.name;
								this.show = false;
								this.showDatabaseAddEditUserDialog = true;
							},
						},
						{
							label: 'Delete User',
							onClick: () => {
								this.show = false;
								confirmDialog({
									title: 'Delete Database User',
									message: `Are you sure you want to delete the database user ?<br>`,
									primaryAction: {
										label: 'Delete',
										variant: 'solid',
										theme: 'red',
										onClick: ({ hide }) => {
											this.$resources.deleteSiteDatabaseUser.submit({
												dt: 'Site Database User',
												dn: row.name,
												method: 'archive',
											});
											this.$resources.deleteSiteDatabaseUser.promise.then(
												() => {
													hide();
													this.show = true;
												},
											);
											return this.$resources.deleteSiteDatabaseUser.promise;
										},
									},
									onSuccess: () => {
										listResource.refresh();
									},
								});
							},
						},
					];
				},
				primaryAction: () => {
					return {
						label: 'Add User',
						variant: 'solid',
						slots: {
							prefix: icon('plus'),
						},
						onClick: () => {
							this.show = false;
							this.selectedUser = null;
							this.showDatabaseAddEditUserDialog = true;
						},
					};
				},
			};
		},
		sitePlan() {
			return this.$site.doc.current_plan;
		},
		planSupportsDatabaseAccess() {
			return this.sitePlan?.database_access;
		},
		$site() {
			return getCachedDocumentResource('Site', this.site);
		},
	},
	methods: {
		hideSiteDatabaseAddEditUserDialog() {
			this.showDatabaseAddEditUserDialog = false;
		},
	},
};
</script>
