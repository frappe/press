<template>
	<Dialog
		:options="{ title: 'Database Audit Logs', size: '3xl' }"
		v-model="show"
	>
		<template #body-content>
			<div
				v-if="loadingFirstPage"
				class="flex justify-center items-center gap-2 py-32 w-full text-ink-gray-7"
			>
				<Spinner class="w-4" />
				Loading
			</div>
			<div v-else>
				<div class="flex justify-end pb-2">
					<Button
						iconLeft="refresh-ccw"
						:loading="$resources.auditLogs.loading"
						@click="$resources.auditLogs.reload()"
					>
						Refresh
					</Button>
				</div>
				<GenericList :options="auditLogsOptions" />
				<div
					class="flex justify-end items-center gap-2 py-3"
					v-if="total > pageSize"
				>
					<p class="text-ink-gray-6 text-sm tnum">{{ pageLabel }}</p>
					<Button
						variant="ghost"
						@click="page--"
						:disabled="page === 1"
						iconLeft="arrow-left"
					>
						Prev
					</Button>
					<Button
						variant="ghost"
						@click="page++"
						:disabled="!hasNextPage"
						iconRight="arrow-right"
					>
						Next
					</Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script>
import { toast } from 'vue-sonner'
import { icon } from '../../utils/components'
import { bytes, date } from '../../utils/format'
import { getToastErrorMessage } from '../../utils/toast'
import GenericList from '../GenericList.vue'

export default {
	name: 'DatabaseAuditLogsDialog',
	props: {
		databaseServer: {
			type: String,
			required: true,
		},
	},
	components: { GenericList },
	emits: ['update:show'],
	data() {
		return {
			show: true,
			page: 1,
			pageSize: 10,
		}
	},
	watch: {
		page() {
			this.$resources.auditLogs.reload()
		},
	},
	resources: {
		auditLogs() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				makeParams: () => ({
					dt: 'Database Server',
					dn: this.databaseServer,
					method: 'get_audit_logs',
					args: {
						start: (this.page - 1) * this.pageSize,
						limit: this.pageSize,
					},
				}),
				auto: true,
			}
		},
		downloadLink() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				auto: false,
			}
		},
	},
	computed: {
		loadingFirstPage() {
			// A refresh keeps the list on screen so the button it was clicked from stays put
			return (
				this.$resources.auditLogs.loading &&
				!this.$resources.auditLogs.data?.message
			)
		},
		logs() {
			return this.$resources.auditLogs.data?.message?.logs || []
		},
		total() {
			return this.$resources.auditLogs.data?.message?.total || 0
		},
		pageStart() {
			return (this.page - 1) * this.pageSize + 1
		},
		pageEnd() {
			return Math.min(this.page * this.pageSize, this.total)
		},
		pageLabel() {
			return `${this.pageStart} - ${this.pageEnd} of ${this.total} audit logs`
		},
		hasNextPage() {
			return this.page * this.pageSize < this.total
		},
		auditLogsOptions() {
			return {
				data: this.logs,
				columns: [
					{
						label: 'From',
						fieldname: 'start_time',
						format: (value) => (value ? date(value, 'lll') : ''),
					},
					{
						label: 'To',
						fieldname: 'end_time',
						format: (value) => (value ? date(value, 'lll') : ''),
					},
					{
						label: 'Size',
						fieldname: 'size_mb',
						align: 'right',
						width: 0.5,
						format: (value) => bytes(value * 1024 * 1024),
					},
					{
						label: '',
						type: 'Button',
						align: 'right',
						width: 0.5,
						Button: ({ row }) => ({
							label: 'Download',
							slots: { prefix: icon('download') },
							onClick: (e) => {
								e.stopPropagation()
								this.downloadAuditLog(row.name)
							},
						}),
					},
				],
			}
		},
	},
	methods: {
		downloadAuditLog(auditLog) {
			toast.promise(
				this.$resources.downloadLink.submit({
					dt: 'Database Server',
					dn: this.databaseServer,
					method: 'get_audit_log_download_link',
					args: { audit_log: auditLog },
				}),
				{
					loading: 'Preparing download...',
					success: (data) => {
						window.open(data.message)
						return 'Download started'
					},
					error: (e) => getToastErrorMessage(e),
				},
			)
		},
	},
}
</script>
