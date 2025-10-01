<template>
	<Dialog
		v-model="show"
		:options="{
			title: 'Login access requests',
			size: 'xl',
		}"
	>
		<template #body-content>
			<ObjectList :options="listOptions" />
		</template>
	</Dialog>
</template>

<script>
import { createResource, getCachedDocumentResource } from 'frappe-ui';
import ObjectList from './ObjectList.vue';
import { date } from '../utils/format';
import { confirmDialog } from '../utils/components';
import { toast } from 'vue-sonner';

export default {
	name: 'SiteLoginRequestDialog',
	props: ['site'],
	components: {
		ObjectList,
	},
	data() {
		return {
			show: true,
		};
	},
	computed: {
		$site() {
			return getCachedDocumentResource('Site', this.site);
		},
		listOptions() {
			return {
				doctype: 'Site Login Consent',
				filters: {
					site: this.site,
				},
				searchField: 'requested_by',
				filterControls() {
					return [
						{
							type: 'select',
							label: 'Status',
							fieldname: 'status',
							options: ['', 'Pending', 'Approved', 'Rejected'],
						},
					];
				},
				columns: [
					{
						label: 'Requested By',
						fieldname: 'requested_by',
						width: '150px',
					},
					{
						label: 'Status',
						fieldname: 'status',
						type: 'Badge',
					},
					{
						label: 'Requested On',
						fieldname: 'creation',
						format: (value) => date(value, 'll'),
					},
				],
				rowActions: ({ row, listResource }) => {
					if (row.status !== 'Pending') {
						return [];
					}

					return [
						{
							label: 'Approve',
							onClick: () => {
								this.show = false;
								confirmDialog({
									title: 'Approve Login Access Request',
									message: `Are you sure you want to approve this request? <strong>${row.requested_by}</strong> will be granted login access to the site.`,
									primaryAction: {
										label: 'Approve',
										variant: 'solid',
										onClick: ({ hide }) => {
											createResource({
												url: 'press.api.client.run_doc_method',
												params: {
													dt: 'Site Login Consent',
													dn: row.name,
													method: 'approve',
												},
												auto: true,
												onSuccess: () => {
													hide();
													this.show = true;
													listResource.refresh();
													toast.success('Login access request approved');
												},
												onError: (err) => {
													toast.error(
														err.messages.length
															? err.messages.join('\n')
															: 'Failed to approve login access request',
													);
												},
											});
										},
									},
								});
							},
						},
						{
							label: 'Reject',
							onClick: () => {
								this.show = false;
								confirmDialog({
									title: 'Reject Login Access Request',
									message: `Are you sure you want to reject this request?`,
									primaryAction: {
										label: 'Reject',
										variant: 'solid',
										theme: 'red',
										onClick: ({ hide }) => {
											createResource({
												url: 'press.api.client.run_doc_method',
												params: {
													dt: 'Site Login Consent',
													dn: row.name,
													method: 'reject',
												},
												auto: true,
												onSuccess: () => {
													hide();
													this.show = true;
													listResource.refresh();
													toast.success('Login access request rejected');
												},
												onError: (err) => {
													toast.error(
														err.messages.length
															? err.messages.join('\n')
															: 'Failed to reject login access request',
													);
												},
											});
										},
									},
								});
							},
						},
					];
				},
			};
		},
	},
};
</script>
