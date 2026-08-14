<template>
	<div class="p-5">
		<div class="flex items-center gap-1.5">
			<Button
				variant="ghost"
				aria-label="Back to backups"
				:route="{ name: 'Site Detail Backups' }"
			>
				<template #icon>
					<lucide-arrow-left class="h-4 w-4" />
				</template>
			</Button>
			<h2 class="text-lg font-medium text-ink-gray-9">Audit Trail</h2>
		</div>

		<ObjectList class="mt-4" :options="options" />

		<SiteBackupAuditDayDialog
			v-if="selectedDay"
			:key="selectedDay.date"
			:day="selectedDay"
			:unconfirmed="history.unconfirmed"
			@close="selectedDay = null"
		/>
	</div>
</template>

<script>
import { Badge } from 'frappe-ui'
import { h } from 'vue'
import { toast } from 'vue-sonner'
import {
	backupType,
	filesDetail,
	filesTheme,
	sizeIsFromRecord,
	sizeLabel,
	statusLabel,
	statusTheme,
} from '../../utils/backupAudit'
import { downloadCSV } from '../../utils/csv'
import dayjs from '../../utils/dayjs'
import { date } from '../../utils/format'
import { getDocResource } from '../../utils/resource'
import { showErrorToast } from '../../utils/toast'
import ObjectList from '../ObjectList.vue'
import SiteBackupAuditDayDialog from './SiteBackupAuditDayDialog.vue'

const DEFAULT_RANGE_DAYS = 30
// The build tells the page when it is done, so nothing is asked for on a timer
const REALTIME_EVENT = 'backup_audit_trail_update'

const SIZE_COLUMNS = [
	{ label: 'Database', fieldname: 'database' },
	{ label: 'Public files', fieldname: 'public' },
	{ label: 'Private files', fieldname: 'private' },
	{ label: 'Config', fieldname: 'config' },
]

export default {
	name: 'SiteBackupAuditTrail',
	props: ['name'],
	components: { ObjectList, SiteBackupAuditDayDialog },
	data() {
		return {
			// Set here, not in created: the resource fetches before the component's own
			// hooks run, and would send nothing. The server trims what it is given.
			startDate: dayjs()
				.subtract(DEFAULT_RANGE_DAYS, 'day')
				.format('YYYY-MM-DD'),
			endDate: dayjs().format('YYYY-MM-DD'),
			selectedDay: null,
		}
	},
	mounted() {
		this.$socket?.on(REALTIME_EVENT, this.onTrailBuilt)
	},
	beforeUnmount() {
		this.$socket?.off(REALTIME_EVENT, this.onTrailBuilt)
	},
	resources: {
		history() {
			return {
				// Its own endpoint rather than a doc method, which would return the whole
				// Site document alongside every answer
				url: 'press.api.site.backup_history',
				initialData: {},
				makeParams: (params) => ({
					name: this.name,
					start_date: this.startDate,
					end_date: this.endDate,
					refresh: params?.refresh ? 1 : 0,
				}),
				auto: true,
				// The dates the pickers show follow the range the trail was built for,
				// which is trimmed to the days this site could have been backed up on
				onSuccess: (data) => {
					if (data?.start_date) this.startDate = data.start_date
					if (data?.end_date) this.endDate = data.end_date
				},
				// A rejected range is an error the server explains, and saying nothing
				// leaves the page looking stuck on the old trail
				onError: showErrorToast,
			}
		},
	},
	computed: {
		site() {
			return getDocResource({ doctype: 'Site', name: this.name })
		},
		siteCreatedOn() {
			return dayjs(this.site.doc?.creation).format('YYYY-MM-DD')
		},
		history() {
			return this.$resources.history.data || {}
		},
		preparing() {
			return this.history.status === 'Preparing'
		},
		broken() {
			return this.history.status === 'Broken'
		},
		rows() {
			// The API already returns one entry per day, ready to render
			return (this.history.days || []).map((day) => ({
				...day,
				name: day.date,
			}))
		},
		banner() {
			// A build that died has already said so, and nothing else will arrive
			if (this.broken) {
				return {
					title:
						"Couldn't put the trail together for this range. Try refresh, and check the error log if it keeps failing.",
					type: 'warning',
					id: `${this.name}-broken`,
				}
			}

			// Records are a query, but the server answers from a queue and the buckets
			// are someone else's network, so the trail is put together in the background
			if (this.preparing) {
				return {
					title:
						'Putting the trail together. This page will fill in on its own.',
					type: 'info',
					id: `${this.name}-preparing`,
				}
			}

			// The server has the last word on days nothing is stored for, so say when it
			// could not be asked rather than letting those days read as no backup
			if (this.history.unconfirmed) {
				return {
					title:
						"Couldn't reach this site's server, so days showing Unconfirmed aren't answered by anything.",
					type: 'general',
					dismissable: true,
					id: `${this.name}-unconfirmed`,
				}
			}

			const plan = this.site.doc?.current_plan
			if (!plan || plan.offsite_backups) return this.retentionBanner
			// Without offsite backups nothing was ever uploaded, so empty days are
			// the plan working as sold rather than a backup that went missing
			return {
				title: `The ${plan.plan_title} plan doesn't store backups offsite, so most days will show No backup.`,
				type: 'general',
				dismissable: true,
				id: `${this.name}-no-offsite`,
			}
		},
		retentionBanner() {
			if (!this.rows.some((row) => row.files === 'Deleted')) return
			// A size against a day whose files are gone is a record, not a promise that
			// the backup can still be restored
			return {
				title:
					'Backups are deleted once their retention period ends. Sizes on those days are what Press recorded when the backup ran.',
				type: 'general',
				dismissable: true,
				id: `${this.name}-retention`,
			}
		},
		columns() {
			return [
				{
					// Every row is a day, and a day recovered from the bucket has no
					// clock time to show, so all of them read as one date
					label: 'Date',
					fieldname: 'date',
					width: 0.9,
					format: (value) => date(value, 'ddd, ll'),
				},
				{
					label: 'Backup',
					fieldname: 'status',
					width: '130px',
					align: 'center',
					type: 'Badge',
					format: (value, row) => statusLabel(row, this.history.unconfirmed),
					theme: (value, row) =>
						statusTheme(statusLabel(row, this.history.unconfirmed)),
				},
				...SIZE_COLUMNS.map((column) => ({
					...column,
					width: 0.6,
					align: 'right',
					type: 'Component',
					component: ({ row }) => this.sizeCell(row, row[column.fieldname]),
				})),
				{
					label: 'Files',
					fieldname: 'files',
					width: 1.1,
					type: 'Component',
					component: ({ row }) => this.filesCell(row),
				},
				{
					label: 'Evidence',
					fieldname: 'source',
					width: 0.9,
					format: (value) => value || 'None',
				},
			]
		},
		options() {
			return {
				data: () => this.rows,
				isLoading: () => this.$resources.history.loading || this.preparing,
				emptyStateMessage: this.preparing
					? 'Putting the trail together'
					: this.broken
						? 'Nothing to show'
						: 'No backups stored for this range',
				banner: () => this.banner,
				onRowClick: (row) => (this.selectedDay = row),
				columns: this.columns,
				filterControls: () => [
					{
						type: 'date',
						label: 'From',
						fieldname: 'startDate',
						local: true,
						default: this.startDate,
					},
					{
						type: 'date',
						label: 'To',
						fieldname: 'endDate',
						local: true,
						default: this.endDate,
					},
				],
				// Picking dates only changes what will be asked for: an audit range is
				// set two controls at a time, and each one would cost a build of its own
				updateFilters: ({ startDate, endDate }) => {
					if (startDate) this.startDate = this.clampToSiteAge(startDate)
					if (endDate) this.endDate = this.clampToSiteAge(endDate)
				},
				actions: () => [
					{
						label: 'Refresh',
						icon: 'refresh-ccw',
						loading: this.$resources.history.loading || this.preparing,
						onClick: () => this.rebuild(),
					},
					{
						label: 'Export as CSV',
						icon: 'download',
						onClick: () => this.exportCSV(),
					},
				],
			}
		},
	},
	methods: {
		sizeCell(row, value) {
			const label = sizeLabel(row, value)
			return h(
				'div',
				{
					class: [
						'w-full truncate text-right text-base',
						label === 'Not recorded' ? 'text-ink-gray-4' : 'text-ink-gray-7',
					],
					// The number is on record, the object it describes is gone
					title: sizeIsFromRecord(row)
						? 'Recorded when the backup ran. The files have since been deleted.'
						: undefined,
				},
				label,
			)
		},
		filesCell(row) {
			const detail = filesDetail(row)
			return h('div', { class: 'flex flex-col gap-0.5 py-1' }, [
				h(Badge, { label: row.files, theme: filesTheme(row.files) }),
				detail ? h('span', { class: 'text-xs text-ink-gray-5' }, detail) : null,
			])
		},
		onTrailBuilt(data) {
			if (data?.site !== this.name) return

			// Match on the range the server says it used, not the one we asked with: it
			// trims a start before the site existed and an end past today
			const { start_date: start, end_date: end } = this.history
			if (!start || (data.start_date === start && data.end_date === end)) {
				this.$resources.history.fetch()
			}
		},
		rebuild() {
			this.$resources.history.fetch({ refresh: true })
		},
		clampToSiteAge(day) {
			if (!this.site.doc?.creation || day >= this.siteCreatedOn) return day
			toast.info(
				`This site was created on ${date(this.siteCreatedOn, 'll')}, so that is the earliest date available.`,
			)
			return this.siteCreatedOn
		},
		exportCSV() {
			// Carries the deletion date and the evidence, so the file stands on its own
			// once it leaves the dashboard
			const rows = this.rows.map((row) => ({
				Date: row.date,
				Backup: statusLabel(row, this.history.unconfirmed),
				...Object.fromEntries(
					SIZE_COLUMNS.map((column) => [
						column.label,
						sizeLabel(row, row[column.fieldname]),
					]),
				),
				Files: row.files,
				'Deleted on': row.expired_on || '',
				'Retention rule': row.rule || '',
				Type: backupType(row),
				Evidence: row.source || '',
			}))
			downloadCSV(
				rows,
				`${this.name}-backup-audit-trail-${this.startDate}-to-${this.endDate}.csv`,
			)
		},
	},
}
</script>
