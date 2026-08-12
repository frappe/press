<template>
	<Dialog
		:options="{
		title: 'Configure Database Audit Trail',
		actions: [
			{
				label: 'Save',
				variant: 'solid',
				loading: $resources.configureAuditTrail.loading,
				disabled: !hasChanges,
				onClick: configureAuditTrail,
			},
		],
	}"
		v-model="show"
	>
		<template #body-content>
			<div class="space-y-4">
				<Switch
					v-model="enabled"
					label="Record an audit trail"
					description="Log every connection and query of this database"
				/>

				<p v-if="isPending" class="text-ink-gray-6 text-p-sm">
					MariaDB is still catching up with your last change.
				</p>

				<template v-if="enabled">
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

					<p v-if="!isEnabled" class="text-ink-gray-6 text-p-sm">
						Your database server will restart once while this is set up, so open
						connections will be dropped briefly.
					</p>

					<p v-if="price" class="text-ink-gray-6 text-p-sm">
						Stored logs are billed at
						<span class="font-medium text-ink-gray-8">{{ price }}</span>
						per GB stored, charged daily, and deleted once they pass the
						retention period.
					</p>
				</template>
			</div>
		</template>
	</Dialog>
</template>
<script>
import { Switch } from 'frappe-ui'
import { toast } from 'vue-sonner'
import { getToastErrorMessage } from '../../utils/toast'

export default {
	name: 'ConfigureDatabaseAuditTrailDialog',
	props: {
		server: {
			type: Object,
			required: true,
		},
	},
	components: { Switch },
	emits: ['update:show'],
	data() {
		return {
			show: true,
			enabled: ['Enabled', 'Enabling'].includes(
				this.server.doc?.database_audit_log_status,
			),
			captureMode: this.server.doc?.database_audit_log_capture_reads
				? 'read-write'
				: 'write',
			retentionDays: this.server.doc?.audit_log_retention_days || 365,
		}
	},
	resources: {
		configureAuditTrail() {
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
		isEnabled() {
			return ['Enabled', 'Enabling'].includes(
				this.server.doc?.database_audit_log_status,
			)
		},
		isPending() {
			return ['Enabling', 'Disabling'].includes(
				this.server.doc?.database_audit_log_status,
			)
		},
		captureReads() {
			return this.captureMode === 'read-write'
		},
		captureModeChanged() {
			return (
				this.captureReads !==
				Boolean(this.server.doc?.database_audit_log_capture_reads)
			)
		},
		hasChanges() {
			if (this.enabled !== this.isEnabled) return true
			if (!this.enabled) return false
			return (
				this.captureModeChanged ||
				this.retentionDays !== this.server.doc?.audit_log_retention_days
			)
		},
		successMessage() {
			// Only retention skips MariaDB, so only retention is immediate
			if (!this.enabled)
				return 'Audit logging will stop once MariaDB is updated, in a few minutes'
			if (!this.isEnabled)
				return 'Setting up audit logging. MariaDB restarts once, so give it a few minutes.'
			if (this.captureModeChanged)
				return 'The new capture mode takes a few minutes to reach MariaDB'
			return 'Retention updated'
		},
		price() {
			const plan = this.$resources.s3StoragePlan.data?.[0]
			if (!plan) return null
			return this.$team.doc.currency === 'INR'
				? `₹${plan.price_inr}`
				: `$${plan.price_usd}`
		},
	},
	methods: {
		configureAuditTrail() {
			// Read before submitting: the message depends on the state we're leaving
			const success = this.successMessage
			toast.promise(
				this.$resources.configureAuditTrail.submit(
					{
						dt: 'Database Server',
						dn: this.server.doc.name,
						method: 'configure_database_audit_log',
						args: {
							enabled: this.enabled,
							capture_reads: this.captureReads,
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
					loading: 'Saving audit trail settings...',
					success,
					error: (e) => getToastErrorMessage(e),
				},
			)
		},
	},
}
</script>
