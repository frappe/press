import { h } from 'vue';
import { icon, renderDialog } from '../../utils/components';
import { getTeam } from '../../data/team';
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
			},
			{
				label: 'Status',
				type: 'Badge',
				fieldname: 'status',
				width: 0.4
			}
		],
		rowActions({ row }) {
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
					label: 'Revert Patch',
					condition: () => row.status === 'Applied',
					onClick: () => {
						// TODO: Hook this up
						console.log('revert patch clicked');
					}
				}
			];
		}
		/*
		primaryAction({ listResource: apps, documentResource: releaseGroup }) {
			return {
				label: 'Apply Patch',
				slots: {
					prefix: icon('plus')
				},
				onClick() {
					renderDialog(
						h(PatchAppDialog, {
							group: releaseGroup.name,
							app: ''
						})
					);
				}
			};
		}
		*/
	}
};
