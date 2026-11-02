import { defineAsyncComponent, h } from 'vue'
import { renderDialog } from '../../utils/components'
import dayjs, { dayjsLocal } from '../../utils/dayjs'
import { planTitle } from '../../utils/format'
import { trialDays } from '../../utils/site'
import type {
	BannerConfig,
	ColumnField,
	DetailBannerConfig,
	DocumentResource,
	Route,
	Row,
} from './types'

export const unreachable = Error('unreachable') // used to indicate that a codepath is unreachable

export const clusterOptions = [
	'',
	'Bahrain',
	'Cape Town',
	'Frankfurt',
	'KSA',
	'London',
	'Mumbai',
	'Singapore',
	'UAE',
	'Virginia',
	'Zurich',
]

const FRAPPE_UPDATE_REMINDER_DAYS = 30
const UPDATE_BENCH_DOCS =
	'https://docs.frappe.io/cloud/benches/updating_a_bench'

// `frappe_updated_on` is when the deployed frappe release was published, so this
// measures the age of the running code, not the time since the last deploy.
export function getFrappeUpdateBanner(
	doc: { frappe_updated_on?: string },
	subject: string,
): DetailBannerConfig | undefined {
	if (!doc.frappe_updated_on) return

	const days = dayjs().diff(dayjsLocal(doc.frappe_updated_on), 'day')
	if (days < FRAPPE_UPDATE_REMINDER_DAYS) return

	return {
		title:
			`${subject} runs Frappe Framework code that is ${days} days old. ` +
			'Update to get the latest fixes and security patches.',
		type: 'warning',
		button: {
			label: 'Learn more',
			variant: 'outline',
			link: UPDATE_BENCH_DOCS,
		},
	}
}

export function getUpsellBanner(site: DocumentResource, title: string) {
	if (
		!site.doc.current_plan ||
		site.doc.current_plan?.private_benches ||
		site.doc.current_plan?.is_trial_plan ||
		!site.doc.group_public
	)
		return

	return {
		title: title,
		dismissable: true,
		id: site.name,
		type: 'general',
		button: {
			label: 'Upgrade Plan',
			variant: 'outline',
			onClick() {
				let SitePlansDialog = defineAsyncComponent(
					() => import('../../components/ManageSitePlansDialog.vue'),
				)
				renderDialog(h(SitePlansDialog, { site: site.name }))
			},
		},
	} satisfies BannerConfig as BannerConfig
}

export function getSitesTabColumns(forBenchTab: boolean) {
	return [
		{
			label: 'Site',
			fieldname: 'host_name',
			format(value, row) {
				return value || row.name
			},
			prefix: () => {
				if (forBenchTab) return
				return h('div', { class: 'ml-2 w-3.5 h-3.5' })
			},
		},
		{
			label: 'Status',
			fieldname: 'status',
			type: 'Badge',
			width: 0.5,
		},
		{
			label: 'Region',
			fieldname: 'cluster_title',
			width: 0.5,
			prefix(row) {
				if (row.cluster_title)
					return h('img', {
						src: row.cluster_image,
						class: 'w-4 h-4',
						alt: row.cluster_title,
					})
			},
		},
		{
			label: 'Plan',
			width: 0.5,
			format(value, row) {
				if (row.trial_end_date) {
					return trialDays(row.trial_end_date)
				}
				return planTitle(row)
			},
		},
	] satisfies ColumnField[] as ColumnField[]
}

export function siteTabFilterControls() {
	return [
		{
			type: 'select',
			label: 'Status',
			fieldname: 'status',
			options: ['', 'Active', 'Inactive', 'Suspended', 'Broken', 'Archived'],
		},
		{
			type: 'select',
			label: 'Region',
			fieldname: 'cluster',
			options: [
				'',
				'Bahrain',
				'Cape Town',
				'Frankfurt',
				'KSA',
				'London',
				'Mumbai',
				'Singapore',
				'UAE',
				'Virginia',
				'Zurich',
			],
		},
	]
}

export function sitesTabRoute(r: Row) {
	return {
		name: 'Site Detail',
		params: { name: r.name },
	} satisfies Route as Route
}
