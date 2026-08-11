<template>
	<Dialog
		:options="{
		title: 'Enable Database Audit Log',
		actions: [
			{
				label: 'Enable',
				variant: 'solid',
				loading: $resources.enableAuditLog.loading,
				onClick: enableAuditLog,
			},
		],
	}"
		v-model="show"
	>
		<template #body-content>
			<div class="space-y-4">
				<p class="text-ink-gray-7 text-p-base">
					Every executed query on this database will be logged on disk.
				</p>

				<FormControl
					v-model="captureMode"
					label="Capture Mode"
					type="select"
					:options="[
					{ label: 'Write queries', value: 'write' },
					{ label: 'Read and write queries', value: 'read-write' },
				]"
					size="sm"
					variant="subtle"
				/>

				<FormControl
					v-model.number="retentionDays"
					label="Retention (days)"
					type="number"
					min="1"
					size="sm"
					variant="subtle"
				/>

				<p class="text-ink-gray-6 text-p-sm">
					Your database server will restart once while this is set up, so open
					connections will be dropped briefly.
				</p>

				<p v-if="price" class="text-ink-gray-6 text-p-sm">
					Archived logs are billed at
					<span class="font-medium text-ink-gray-8">{{ price }}</span>
					per GB stored, charged daily, and deleted once they pass the retention
					period.
				</p>
			</div>
		</template>
	</Dialog>
</template>
<script>
import { toast } from 'vue-sonner'
import { getToastErrorMessage } from '../../utils/toast'

export default {
	name: 'EnableDatabaseAuditLogDialog',
	props: {
		server: {
			type: Object,
			required: true,
		},
	},
	emits: ['update:show'],
	data() {
		return {
			show: true,
			captureMode: 'write',
			retentionDays: this.server.doc?.audit_log_retention_days || 365,
		}
	},
	resources: {
		enableAuditLog() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				auto: false,
			}
		},
		s3StoragePlan() {
			return {
				url: 'press.api.client.get_list',
				params: {
					doctype: 'S3 Storage Plan',
					filters: { enabled: 1 },
					fields: ['name', 'price_inr', 'price_usd'],
					limit: 1,
				},
				auto: true,
			}
		},
	},
	computed: {
		price() {
			const plan = this.$resources.s3StoragePlan.data?.[0]
			if (!plan) return null
			return this.$team.doc.currency === 'INR'
				? `₹${plan.price_inr}`
				: `$${plan.price_usd}`
		},
	},
	methods: {
		enableAuditLog() {
			toast.promise(
				this.$resources.enableAuditLog.submit(
					{
						dt: 'Database Server',
						dn: this.server.doc.name,
						method: 'enable_database_audit_log',
						args: {
							capture_reads: this.captureMode === 'read-write',
							retention_days: this.retentionDays,
						},
					},
					{
						onSuccess: () => {
							this.show = false
							this.server.reload()
						},
					},
				),
				{
					loading: 'Enabling audit logging...',
					success:
						'Audit logging is being enabled. MariaDB will restart shortly.',
					error: (e) => getToastErrorMessage(e),
				},
			)
		},
	},
}
</script>
