import { toast } from 'vue-sonner';
import { getTeam } from '../../data/team';
import { confirmDialog, icon, renderDialog } from '../../utils/components';
import { h } from 'vue';
import PatchAppDialog from '../../components/group/PatchAppDialog.vue';
import { ColumnField, FilterField, Tab } from './types';
import { isMobile } from '../../utils/device';

const statusTheme = {
	Applied: 'green',
	'Not Applied': 'gray',
	'In Process': 'orange',
	Failure: 'red',
};

type Status = keyof typeof statusTheme;

export function getPatchesTab(forBench: boolean) {
	return {
		label: 'Patches',
		icon: icon('hash'),
		route: 'patches',
		type: 'list',
		list: {
			experimental: true, // If removing this, uncheck App Patch doctype beta flag.
			documentation: 'https://frappecloud.com/docs/benches/app-patches',
			doctype: 'App Patch',
			filters: (res) => ({ [forBench ? 'bench' : 'group']: res.name }),
			searchField: 'filename',
			filterControls: (r) =>
				[
					{
						type: 'select',
						label: 'Status',
						fieldname: 'status',
						options: ['', 'Not Applied', 'In Process', 'Failed', 'Applied'],
					},
					{
						type: 'select',
						label: 'App',
						fieldname: 'app',
						class: !isMobile() ? 'w-24' : '',
						options: [
							'',
							...new Set(r.listResource.data?.map((i) => String(i.app)) || []),
						],
					},
				] satisfies FilterField[],
			columns: getPatchesTabColumns(forBench),
			primaryAction({ listResource: apps, documentResource: doc }) {
				return {
					label: 'Apply Patch',
					slots: {
						prefix: icon('plus'),
					},
					onClick() {
						const group = doc.doctype === 'Bench' ? doc.doc.group : doc.name;

						renderDialog(h(PatchAppDialog, { group: group, app: '' }));
					},
				};
			},
			rowActions({ row, listResource }) {
				let team = getTeam();
				return [
					{
						label: 'View in Desk',
						condition: () => team.doc?.is_desk_user,
						onClick() {
							window.open(
								`${window.location.protocol}//${window.location.host}/app/app-patch/${row.name}`,
								'_blank'
							);
						},
					},
					{
						label: 'Apply Patch',
						condition: () => row.status !== 'In Process',
						onClick: () => {
							toast.promise(
								listResource.runDocMethod.submit({
									method: 'apply_patch',
									name: String(row.name),
								}),
								{
									loading: 'Creating job to apply patch',
									success: () => 'Patch apply in process',
									error: () => 'Failed to apply patch',
								}
							);
						},
					},
					{
						label: 'Revert Patch',
						condition: () => row.status !== 'In Process',
						onClick: () => {
							toast.promise(
								listResource.runDocMethod.submit({
									method: 'revert_patch',
									name: String(row.name),
								}),
								{
									loading: 'Creating job to revert patch',
									success: () => 'Patch reversion in process',
									error: () => 'Failed to revert patch',
								}
							);
						},
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
											onSuccess: () => hide(),
										}),
										{
											loading: 'Deleting...',
											success: () => 'Patch deleted',
											error: () => 'Failed to delete patch',
										}
									);
								},
							});
						},
					},
				];
			},
		},
	} satisfies Tab;
}

function getPatchesTabColumns(forBench: boolean) {
	const columns: ColumnField[] = [
		{
			label: 'File Name',
			fieldname: 'filename',
			width: forBench ? '400px' : '200px',
		},
		{
			label: 'App',
			fieldname: 'app',
			width: 0.4,
		},
		{
			label: 'Status',
			type: 'Badge',
			fieldname: 'status',
			theme: (value) => statusTheme[value as Status],
			width: 0.4,
		},
		{
			label: 'Bench',
			fieldname: 'bench',
			width: 0.8,
		},
		{
			label: 'Patch URL',
			fieldname: 'url',
			width: forBench ? undefined : '300px',
			format(value) {
				if (!value) {
					return '-';
				}

				const url = new URL(value);
				return url.hostname + url.pathname;
			},
			link: (value) => String(value),
		},
	];

	if (forBench) return columns.filter((f) => f.fieldname !== 'bench');
	return columns;
}
