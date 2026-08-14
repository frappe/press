<template>
	<Dialog :options="{ title: title, size: 'lg' }" v-model="show">
		<template #body-content>
			<div v-if="day" class="divide-y divide-outline-gray-1">
				<div
					v-for="entry in entries"
					:key="entry.label"
					class="flex items-baseline justify-between gap-4 py-2 text-base"
				>
					<span class="text-ink-gray-5">{{ entry.label }}</span>
					<span class="text-right text-ink-gray-8">{{ entry.value }}</span>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script>
import { Dialog } from 'frappe-ui'
import {
	backupType,
	sizeLabel,
	statusLabel,
	totalSize,
} from '../../utils/backupAudit'
import { date } from '../../utils/format'

export default {
	name: 'SiteBackupAuditDayDialog',
	props: ['day', 'unconfirmed'],
	components: { Dialog },
	data() {
		return { show: true }
	},
	watch: {
		show(value) {
			if (!value) this.$emit('close')
		},
	},
	computed: {
		title() {
			return this.day ? date(this.day.date, 'dddd, ll') : ''
		},
		entries() {
			const day = this.day
			// Only what this day's source could answer for: an audit is worth nothing
			// if the page fills the gaps in itself
			return [
				{ label: 'Backup', value: statusLabel(day, this.unconfirmed) },
				{ label: 'Started', value: day.started_at ? date(day.started_at) : '' },
				{ label: 'Type', value: backupType(day) },
				{ label: 'Database', value: sizeLabel(day, day.database) },
				{ label: 'Public files', value: sizeLabel(day, day.public) },
				{ label: 'Private files', value: sizeLabel(day, day.private) },
				{ label: 'Config', value: sizeLabel(day, day.config) },
				{ label: 'Total size', value: totalSize(day) },
				{ label: 'Files', value: day.files },
				{
					label: 'Deleted on',
					value: day.expired_on ? date(day.expired_on) : '',
				},
				{
					label: 'Kept till',
					value: day.keep_till ? date(day.keep_till, 'll') : '',
				},
				{ label: 'Retention rule', value: day.rule || '' },
				{ label: 'Evidence', value: day.source || 'No source could answer' },
			].filter((entry) => entry.value)
		},
	},
}
</script>
