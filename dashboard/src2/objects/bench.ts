import type { VNode } from 'vue';
import { h } from 'vue';
import { getTeam } from '../data/team';
import { icon } from '../utils/components';
import { clusterOptions } from './common';
import { getAppsTab } from './common/apps';
import type {
	DashboardObject,
	Detail,
	FilterField,
	List,
	Row,
	Tab
} from './common/types';
import { getJobsTab } from './common/jobs';

export default {
	doctype: 'Bench',
	whitelistedMethods: {},
	detail: getDetail(),
	list: getList(),
	routes: [
		{
			name: 'Bench Job',
			path: 'jobs/:id',
			component: () => import('../pages/JobPage.vue')
		}
	]
} satisfies DashboardObject as DashboardObject;

function getDetail() {
	return {
		titleField: 'name',
		statusBadge: ({ documentResource: bench }) => ({ label: bench.doc.status }),
		route: '/benches/:name',
		tabs: getTabs(),
		actions: () => [],
		breadcrumbs: ({ items, documentResource: bench }) => {
			const $team = getTeam();
			const benchCrumb = {
				label: bench.doc?.name,
				route: `/benches/${bench.doc?.name}`
			};

			if (bench.doc.group_team == $team.doc?.name || $team.doc?.is_desk_user) {
				return [
					{
						label: bench.doc?.group_title,
						route: `/groups/${bench.doc?.group}`
					},
					benchCrumb
				];
			}

			return [...items.slice(0, -1), benchCrumb];
		}
	} satisfies Detail as Detail;
}

function getTabs() {
	return [getAppsTab(false), getJobsTab('Bench')] satisfies Tab[] as Tab[];
}

function getList() {
	return {
		route: '/benches',
		title: 'Benches',
		fields: [
			'group.title as group_title',
			'cluster.name as cluster_name',
			'cluster.image as cluster_image',
			'cluster.title as cluster_title'
		],
		orderBy: 'creation desc',
		searchField: 'name',
		columns: [
			{
				label: 'Bench',
				fieldname: 'name',
				width: 1.5,
				class: 'font-medium',
				suffix: getBenchTitleSuffix
			},
			{ label: 'Status', fieldname: 'status', type: 'Badge', width: 0.6 },
			{ label: 'Sites', fieldname: 'site_count', type: 'Number' },
			{
				label: 'Region',
				fieldname: 'cluster',
				width: 1,
				format: (value, row) => String(row.cluster_title || value || ''),
				prefix: getClusterImagePrefix
			},
			{ label: 'Bench Group', fieldname: 'group_title' }
		],
		filterControls
	} satisfies List as List;
}

function getBenchTitleSuffix(row: Row) {
	const ch: VNode[] = [];
	if (row.inplace_update_docker_image) ch.push(getInPlaceUpdatesSuffix(row));
	if (row.has_app_patch_applied) ch.push(getAppPatchSuffix(row));
	if (!ch.length) return;

	return h(
		'div',
		{
			class: 'flex flex-row gap-2'
		},
		ch
	);
}

function getInPlaceUpdatesSuffix(row: Row) {
	const count = Number(
		String(row.inplace_update_docker_image).split('-').at(-1)
	);

	let title = 'Bench has been updated in place';
	if (!Number.isNaN(count) && count > 1) {
		title += ` ${count} times`;
	}

	return h(
		'div',
		{
			title,
			class: 'rounded-full bg-gray-100 p-1'
		},
		h(icon('star', 'w-3 h-3'))
	);
}

function getAppPatchSuffix(row: Row) {
	return h(
		'div',
		{
			title: 'Apps in this bench may have been patched',
			class: 'rounded-full bg-gray-100 p-1'
		},
		h(icon('hash', 'w-3 h-3'))
	);
}

function getClusterImagePrefix(row: Row) {
	if (!row.cluster_image) return;

	return h('img', {
		src: row.cluster_image,
		class: 'w-4 h-4',
		alt: row.cluster_title
	});
}

function filterControls() {
	return [
		{
			type: 'select',
			label: 'Status',
			fieldname: 'status',
			options: [
				'',
				'Active',
				'Pending',
				'Installing',
				'Updating',
				'Broken',
				'Archived'
			]
		},
		{
			type: 'link',
			label: 'Bench Group',
			fieldname: 'group',
			options: {
				doctype: 'Release Group'
			}
		},
		{
			type: 'select',
			label: 'Region',
			fieldname: 'cluster',
			options: clusterOptions
		}
	] satisfies FilterField[] as FilterField[];
}
