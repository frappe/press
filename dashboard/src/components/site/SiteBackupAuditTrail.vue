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
	</div>
</template>

<script>
import { toast } from 'vue-sonner'
import { downloadCSV } from '../../utils/csv'
import dayjs from '../../utils/dayjs'
import { bytes, date } from '../../utils/format'
import { getDocResource } from '../../utils/resource'
import ObjectList from '../ObjectList.vue'

const DEFAULT_RANGE_DAYS = 30
const POLL_MS = 5000
const MAX_POLLS = 24

export default {
	name: 'SiteBackupAuditTrail',
	props: ['name'],
	components: { ObjectList },
	data() {
		return {
			startDate: null,
			endDate: dayjs().format('YYYY-MM-DD'),
			pollTimer: null,
			polls: 0,
		}
	},
	beforeUnmount() {
		clearTimeout(this.pollTimer)
	},
	created() {
		this.startDate = this.clampToSiteAge(
			dayjs().subtract(DEFAULT_RANGE_DAYS, 'day').format('YYYY-MM-DD'),
			{ quiet: true },
		)
	},
	resources: {
		history() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				makeParams: (params) => ({
					dt: 'Site',
					dn: this.name,
					method: 'get_backup_history',
					args: {
						start_date: this.startDate,
						end_date: this.endDate,
						refresh: params?.refresh ? 1 : 0,
					},
				}),
				auto: true,
				// Re-armed on every answer: watching the flag would stop after one look,
				// because a second Preparing in a row is not a change
				onSuccess: () => this.pollWhilePreparing(),
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
			return this.$resources.history.data?.message || {}
		},
		preparing() {
			return this.history.status === 'Preparing'
		},
		rows() {
			// The API already returns one entry per day, ready to render
			return (this.history.days || []).map((day) => ({
				...day,
				name: day.date,
			}))
		},
		banner() {
			// Records are a query, but the server answers from a queue and the buckets
			// are someone else's network, so the trail is put together in the background
			if (this.preparing) {
				return {
					title:
						this.polls < MAX_POLLS
							? 'Putting the trail together. This page will fill in on its own.'
							: 'This is taking longer than usual. Hit Refresh to look again.',
					type: 'info',
					id: `${this.name}-preparing`,
				}
			}

			// The server has the last word on days nothing is stored for, so say when it
			// could not be asked rather than letting those days read as no backup
			if (this.history.unconfirmed) {
				return {
					title:
						"Couldn't reach this site's server, so days showing Not Available aren't confirmed.",
					type: 'general',
					dismissable: true,
					id: `${this.name}-unconfirmed`,
				}
			}

			const plan = this.site.doc?.current_plan
			if (!plan || plan.offsite_backups) return
			// Without offsite backups nothing was ever uploaded, so empty days are
			// the plan working as sold rather than a backup that went missing
			return {
				title: `The ${plan.plan_title} plan doesn't store backups offsite, so most days will show Not Available.`,
				type: 'general',
				dismissable: true,
				id: `${this.name}-no-offsite`,
			}
		},
		options() {
			return {
				data: () => this.rows,
				isLoading: () => this.$resources.history.loading || this.preparing,
				emptyStateMessage: this.preparing
					? 'Putting the trail together'
					: 'No backups stored for this range',
				banner: () => this.banner,
				columns: [
					{
						// Every row is a day, and a day recovered from the bucket has no
						// clock time to show, so all of them read as one date
						label: 'Timestamp',
						fieldname: 'date',
						width: 1,
						format: (value) => date(value, 'ddd, ll'),
					},
					{
						label: 'Status',
						fieldname: 'status',
						width: '150px',
						align: 'center',
						type: 'Badge',
						theme: (value) =>
							({ Success: 'green', Failure: 'red' })[value] || 'gray',
					},
					{
						label: 'Database',
						fieldname: 'database',
						width: 0.5,
						format: (value) => (value ? bytes(value) : ''),
					},
					{
						label: 'Public Files',
						fieldname: 'public',
						width: 0.5,
						format: (value) => (value ? bytes(value) : ''),
					},
					{
						label: 'Private Files',
						fieldname: 'private',
						width: 0.5,
						format: (value) => (value ? bytes(value) : ''),
					},
					{
						// Often the only thing left on an old day, and then it is the
						// whole basis for calling that day a backup
						label: 'Config',
						fieldname: 'config',
						width: 0.5,
						format: (value) => (value ? bytes(value) : ''),
					},
				],
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
				updateFilters: ({ startDate, endDate }) => {
					if (startDate) this.startDate = this.clampToSiteAge(startDate)
					if (endDate) this.endDate = this.clampToSiteAge(endDate)
					this.polls = 0
					this.$resources.history.fetch()
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
		pollWhilePreparing() {
			clearTimeout(this.pollTimer)
			if (!this.preparing || this.polls >= MAX_POLLS) return
			this.polls += 1
			this.pollTimer = setTimeout(
				() => this.$resources.history.fetch(),
				POLL_MS,
			)
		},
		rebuild() {
			this.polls = 0
			this.$resources.history.fetch({ refresh: true })
		},
		clampToSiteAge(day, { quiet = false } = {}) {
			if (!this.site.doc?.creation || day >= this.siteCreatedOn) return day
			if (!quiet) {
				toast.info(
					`This site was created on ${date(this.siteCreatedOn, 'll')}, so that is the earliest date available.`,
				)
			}
			return this.siteCreatedOn
		},
		exportCSV() {
			// Built from the columns themselves, so the file always matches the screen
			const rows = this.rows.map((row) => ({
				Date: row.date,
				...Object.fromEntries(
					this.options.columns.map((column) => [
						column.label,
						column.format
							? column.format(row[column.fieldname], row)
							: row[column.fieldname],
					]),
				),
			}))
			downloadCSV(
				rows,
				`${this.name}-backup-audit-trail-${this.startDate}-to-${this.endDate}.csv`,
			)
		},
	},
}
</script>
