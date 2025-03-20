import { defineAsyncComponent, h } from 'vue';
import { toast } from 'vue-sonner';
import { getTeam } from '../../data/team';
import router from '../../router';
import { confirmDialog, icon, renderDialog } from '../../utils/components';
import { planTitle } from '../../utils/format';
import type {
	ColumnField,
	DialogConfig,
	FilterField,
	Tab,
	TabList,
} from './types';
import { getUpsellBanner } from '.';
import { isMobile } from '../../utils/device';
import { getToastErrorMessage } from '../../utils/toast';

export function getAppsTab(forSite: boolean) {
	return {
		label: 'Apps',
		icon: icon('grid'),
		route: 'apps',
		type: 'list',
		condition: (docResource) =>
			forSite && docResource.doc?.status !== 'Archived',
		list: getAppsTabList(forSite),
	} satisfies Tab as Tab;
}

function getAppsTabList(forSite: boolean) {
	const options = forSite ? siteAppListOptions : benchAppListOptions;
	const list: TabList = {
		doctype: '',
		filters: () => ({}),
		...options,
		columns: getAppsTabColumns(forSite),
		searchField: !forSite ? 'title' : undefined,
		filterControls: (r) => {
			if (forSite) return [];
			else
				return [
					{
						type: 'select',
						label: 'Branch',
						class: !isMobile() ? 'w-24' : '',
						fieldname: 'branch',
						options: [
							'',
							...new Set(
								r.listResource.data?.map((i) => String(i.branch)) || []
							),
						],
					},
					{
						type: 'select',
						label: 'Owner',
						class: !isMobile() ? 'w-24' : '',
						fieldname: 'repository_owner',
						options: [
							'',
							...new Set(
								r.listResource.data?.map(
									(i) => String(i.repository_url).split('/').at(-2) || ''
								) || []
							),
						],
					},
				] satisfies FilterField[];
		},
	};

	return list;
}

function getAppsTabColumns(forSite: boolean) {
	const appTabColumns: ColumnField[] = [
		{
			label: 'App',
			fieldname: 'title',
			width: 1,
			suffix(row) {
				if (!row.is_app_patched) {
					return;
				}

				return h(
					'div',
					{
						title: 'App has been patched',
						class: 'rounded-full bg-gray-100 p-1',
					},
					h(icon('hash', 'w-3 h-3'))
				);
			},
			format: (value, row) => value || row.app_title,
		},
		{
			label: 'Plan',
			width: 0.75,
			class: 'text-gray-600 text-sm',
			format(_, row) {
				const planText = planTitle(row.plan_info);
				if (planText) return `${planText}/mo`;
				else return 'Free';
			},
		},
		{
			label: 'Repository',
			fieldname: 'repository_url',
			format: (value) => String(value).split('/').slice(-2).join('/'),
			link: (value) => String(value),
		},
		{
			label: 'Branch',
			fieldname: 'branch',
			type: 'Badge',
			width: 1,
			link: (value, row) => {
				return `${row.repository_url}/tree/${value}`;
			},
		},
		{
			label: 'Commit',
			fieldname: 'hash',
			type: 'Badge',
			width: 1,
			link: (value, row) => {
				return `${row.repository_url}/commit/${value}`;
			},
			format(value) {
				return String(value).slice(0, 7);
			},
		},
		{
			label: 'Commit Message',
			fieldname: 'commit_message',
			width: '30rem',
		},
	];

	if (forSite) return appTabColumns;
	return appTabColumns.filter((c) => c.label !== 'Plan');
}

const siteAppListOptions: Partial<TabList> = {
	doctype: 'Site App',
	filters: (res) => {
		return { parenttype: 'Site', parent: res.doc?.name };
	},
	banner({ documentResource: site }) {
		const bannerTitle =
			'Your site is currently on a shared bench group. Upgrade plan to install custom apps, enable server scripts and <a href="https://frappecloud.com/shared-hosting#benches" class="underline" target="_blank">more</a>.';

		return getUpsellBanner(site, bannerTitle);
	},
	primaryAction({ listResource: apps, documentResource: site }) {
		return {
			label: 'Install App',
			slots: {
				prefix: icon('plus'),
			},
			onClick() {
				const InstallAppDialog = defineAsyncComponent(
					() => import('../../components/site/InstallAppDialog.vue')
				);

				renderDialog(
					h(InstallAppDialog, {
						site: site.name,
						onInstalled() {
							apps.reload();
						},
					})
				);
			},
		};
	},
	rowActions({ row, listResource: apps, documentResource: site }) {
		let $team = getTeam();

		return [
			{
				label: 'View in Desk',
				condition: () => $team.doc?.is_desk_user,
				onClick() {
					window.open(`/app/app-source/${row.name}`, '_blank');
				},
			},
			{
				label: 'Change Plan',
				condition: () => row.plan_info && row.plans.length > 1,
				onClick() {
					let SiteAppPlanChangeDialog = defineAsyncComponent(
						() => import('../../components/site/SiteAppPlanSelectDialog.vue')
					);
					renderDialog(
						h(SiteAppPlanChangeDialog, {
							app: row,
							currentPlan: row.plans.find(
								(plan: Record<string, any>) => plan.name === row.plan_info.name
							),
							onPlanChanged() {
								apps.reload();
							},
						})
					);
				},
			},
			{
				label: 'Uninstall',
				condition: () => row.app !== 'frappe',
				onClick() {
					const UninstallAppDialog = defineAsyncComponent(
						() => import('../../components/site/UninstallAppDialog.vue')
					);
					renderDialog(
						h(UninstallAppDialog, {
							app: row,
							site: site,
						})
					);
				},
			},
		];
	},
};

const benchAppListOptions: Partial<TabList> = {
	doctype: 'Bench App',
	filters: (res) => {
		return { parenttype: 'Bench', parent: res.doc?.name };
	},
	rowActions({ row }) {
		let $team = getTeam();
		return [
			{
				label: 'View in Desk',
				condition: () => $team.doc?.is_desk_user,
				onClick() {
					window.open(`/app/app-release/${row.release}`, '_blank');
				},
			},
		];
	},
};
