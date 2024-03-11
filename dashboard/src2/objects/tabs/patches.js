import { toast } from 'vue-sonner';
import { getTeam } from '../../data/team';
import { confirmDialog, icon, renderDialog } from '../../utils/components';
import { h } from 'vue';
import PatchAppDialog from '../../components/bench/PatchAppDialog.vue';

export default {
	label: 'Patches',
	icon: icon('hash'),
	route: 'patches',
	type: 'list',
	list: {
		doctype: 'App Patch',
		filters: releaseGroup => {
			return {
				group: releaseGroup.name
			};
		},
		columns: [
			{
				label: 'File Name',
				fieldname: 'filename',
				width: 0.75
			},
			{
				label: 'Status',
				type: 'Badge',
				fieldname: 'status',
				width: 0.4
			},
			{
				label: 'Deploy Name',
				fieldname: 'bench',
				width: 1
			},
			{
				label: 'App',
				fieldname: 'app',
				width: 0.6
			},
			{
				label: 'Patch URL',
				fieldname: 'url',
				width: 1,
				format(value) {
					if (!value) {
						return '-';
					}

					const url = new URL(value);
					return url.hostname + url.pathname;
				},
				link(value) {
					return value;
				}
			}
		],
		primaryAction({ listResource: apps, documentResource: releaseGroup }) {
			return {
				label: 'Apply Patch',
				slots: {
					prefix: icon('plus')
				},
				onClick() {
					renderDialog(
						h(PatchAppDialog, { group: releaseGroup.name, app: '' })
					);
				}
			};
		},
		rowActions({ row, listResource }) {
			let team = getTeam();
			return [
				{
					label: 'View in Desk',
					condition: () => team.doc.is_desk_user,
					onClick() {
						window.open(
							`${window.location.protocol}//${window.location.host}/app/app-patch/${row.name}`,
							'_blank'
						);
					}
				},
				{
					label: 'Apply Patch',
					condition: () => row.status === 'Not Applied',
					onClick: () => {
						toast.promise(
							listResource.runDocMethod.submit({
								method: 'apply_patch',
								name: row.name
							}),
							{
								loading: 'Applying...',
								success: 'Patch applied',
								error: 'Failed to apply patch'
							}
						);
					}
				},
				{
					label: 'Revert Patch',
					condition: () => row.status === 'Applied',
					onClick: () => {
						toast.promise(
							listResource.runDocMethod.submit({
								method: 'revert_patch',
								name: row.name
							}),
							{
								loading: 'Reverting...',
								success: 'Patch reverted',
								error: 'Failed to revert patch'
							}
						);
					}
				},
				{
					label: 'Delete',
					condition: () => row.status === 'Not Applied',
					onClick: () => {
						confirmDialog({
							title: 'Delete Patch',
							message: 'Are you sure you want to delete this patch?',
							onSuccess: ({ hide }) => {
								toast.promise(
									listResource.delete.submit(row.name, {
										onSuccess: () => hide()
									}),
									{
										loading: 'Deleting...',
										success: 'Patch deleted',
										error: 'Failed to delete patch'
									}
								);
							}
						});
					}
				}
			];
		}
	}
};
