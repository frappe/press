<template>
	<!-- Keyed so switching mode builds a fresh list rather than reusing the other one's resource -->
	<ObjectList :key="mode" :options="options" />
</template>

<script>
import { backupRecordsOptions } from '../../objects/site/backups'
import { downloadCSV } from '../../utils/csv'
import dayjs from '../../utils/dayjs'
import { bytes, date } from '../../utils/format'
import ObjectList from '../ObjectList.vue'

const DEFAULT_RANGE_DAYS = 30

export default {
	name: 'SiteBackups',
	props: {
		documentResource: {
			type: Object,
			required: true,
		},
	},
	components: { ObjectList },
	data() {
		return {
			mode: 'records',
			startDate: dayjs()
				.subtract(DEFAULT_RANGE_DAYS, 'day')
				.format('YYYY-MM-DD'),
			endDate: dayjs().format('YYYY-MM-DD'),
		}
	},
	resources: {
		history() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				makeParams: () => ({
					dt: 'Site',
					dn: this.documentResource.doc?.name,
					method: 'get_backup_history',
					args: { start_date: this.startDate, end_date: this.endDate },
				}),
				auto: false,
			}
		},
	},
	computed: {
		context() {
			return { documentResource: this.documentResource }
		},
		options() {
			return this.mode === 'history' ? this.historyOptions : this.recordsOptions
		},
		historyControl() {
			return {
				type: 'checkbox',
				label: 'Audit Trail',
				fieldname: 'history',
				local: true,
				default: this.mode === 'history',
			}
		},
		recordsOptions() {
			const options = backupRecordsOptions()
			return {
				...options,
				context: this.context,
				filters: options.filters(this.documentResource),
				filterControls: (context) => [
					...options.filterControls(context),
					this.historyControl,
				],
				updateFilters: (filters) => {
					if (filters.history !== undefined)
						return this.setMode(filters.history)
					options.updateFilters(filters)
				},
			}
		},
		historyOptions() {
			return {
				context: this.context,
				data: () => this.historyRows,
				isLoading: () => this.$resources.history.loading,
				emptyStateMessage: 'No backups stored for this range',
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
						theme: (value) => (value === 'Success' ? 'green' : 'gray'),
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
					this.historyControl,
				],
				updateFilters: ({ history, startDate, endDate }) => {
					if (history !== undefined) return this.setMode(history)
					if (startDate) this.startDate = startDate
					if (endDate) this.endDate = endDate
					this.$resources.history.fetch()
				},
				actions: () => [
					{
						label: 'Refresh',
						icon: 'refresh-ccw',
						loading: this.$resources.history.loading,
						onClick: () => this.$resources.history.fetch(),
					},
					{
						label: 'Export as CSV',
						icon: 'download',
						onClick: () => this.exportHistory(),
					},
				],
			}
		},
		historyRows() {
			// The API already returns one entry per day, ready to render
			return (this.$resources.history.data?.message || []).map((day) => ({
				...day,
				name: day.date,
			}))
		},
	},
	methods: {
		exportHistory() {
			// Built from the columns themselves, so the file always matches the screen
			const rows = this.historyRows.map((row) => ({
				Date: row.date,
				...Object.fromEntries(
					this.historyOptions.columns.map((column) => [
						column.label,
						column.format
							? column.format(row[column.fieldname], row)
							: row[column.fieldname],
					]),
				),
			}))
			const site = this.documentResource.doc.name
			downloadCSV(
				rows,
				`${site}-backup-audit-trail-${this.startDate}-to-${this.endDate}.csv`,
			)
		},
		setMode(showHistory) {
			this.mode = showHistory ? 'history' : 'records'
			if (this.mode === 'history') this.$resources.history.fetch()
		},
	},
}
</script>
