<template>
	<div class="flex flex-col gap-4 p-4 divide-y border rounded">
		<ObjectList :options="leadfollowups" />
	</div>
</template>
<script setup>
import { useRoute } from 'vue-router';
import { computed, h } from 'vue';
import ObjectList from '../ObjectList.vue';
import UpdateFollowupDialog from './UpdateFollowupDialog.vue';
import { confirmDialog, renderDialog } from '../../utils/components';
import { toast } from 'vue-sonner';
import { createResource } from 'frappe-ui';
import { date } from '../../utils/format';

const route = useRoute();

const showUpdateFollowupDialog = defineModel(false);
const leadfollowups = computed(() => {
	return {
		doctype: 'Lead Followup',
		filters: {
			parent: route.params.leadId,
			parenttype: 'Partner Lead',
		},
		columns: [
			{
				label: 'Date',
				fieldname: 'date',
				width: '100px',
				format(value) {
					return date(value, 'll');
				},
			},
			{
				label: 'Followup By',
				fieldname: 'followup_by',
			},
			{
				label: 'Communication',
				fieldname: 'communication_type',
			},
			{
				label: 'Spoke To',
				fieldname: 'spoke_to',
			},
			{
				label: 'Notes',
				fieldname: 'discussion',
				class: 'break-all',
				width: '200px',
			},
		],
		rowActions: ({ row }) => {
			return [
				{
					label: 'Update',
					onClick: () => {
						return renderDialog(
							h(UpdateFollowupDialog, {
								modelValue: true,
								id: row.name,
								leadId: route.params.leadId,
							}),
						);
					},
				},
				{
					label: 'Remove',
					onClick: () => {
						confirmDialog({
							title: 'Delete Followup',
							message:
								'Are you sure you want to delete this followup from ' +
								row.followup_by +
								'?',
							primaryAction: {
								label: 'Delete',
								variant: 'solid',
								theme: 'red',
								onClick: ({ hide }) => {
									return deleteFollowup
										.submit({
											id: row.name,
											lead_name: route.params.leadId,
										})
										.then(hide);
								},
							},
						});
					},
				},
			];
		},
		primaryAction: () => {
			return {
				label: 'Add Followup',
				variant: 'solid',
				slots: {
					prefix: 'plus',
				},
				onClick: () => {
					showUpdateFollowupDialog.value = true;
					return renderDialog(
						h(UpdateFollowupDialog, {
							modelValue: true,
							id: '',
							leadId: route.params.leadId,
						}),
					);
				},
			};
		},
	};
});

const deleteFollowup = createResource({
	url: 'press.api.partner.delete_followup',
	onSuccess: () => {
		toast.success('Followup deleted successfully');
	},
});
</script>
