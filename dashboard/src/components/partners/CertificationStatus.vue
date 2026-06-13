<template>
	<div>
		<Dialog
			:show="show"
			v-model="show"
			title="Certification Request Status"
			size="xl"
		>
			<ObjectList :options="requestList"></ObjectList>
		</Dialog>
	</div>
</template>
<script setup>
import { ref, computed, h } from 'vue'
import { createResource } from 'frappe-ui'
import ObjectList from '../ObjectList.vue'
import { renderDialog } from '../../utils/components'
import CertificateSummary from './CertificateSummary.vue'
import { session } from '../../data/session'

const show = ref(true)
const $session = session || {}

const certRequestList = createResource({
	url: 'press.api.partner.get_certification_requests',
	auto: true,
	initialData: [],
	transform: (data) => {
		return (
			data?.map((row) => {
				return {
					member_name: row.name,
					certificate_type: row.course,
					status: row.status,
					summary: row.summary || '',
				}
			}) || []
		)
	},
})
const requestList = computed(() => {
	return {
		data: () => certRequestList.data,
		columns: [
			{
				label: 'Member Name',
				fieldname: 'member_name',
				width: 1,
			},
			{
				label: 'Certificate Type',
				fieldname: 'certificate_type',
				width: 1,
			},
			{
				label: 'Status',
				fieldname: 'status',
				width: 0.5,
				align: 'center',
				type: 'Badge',
			},
		],
		orderBy: 'creation desc',
		onRowClick: (row) => {
			if (row.summary && $session.isSystemUser) {
				return renderDialog(
					h(CertificateSummary, {
						modelValue: true,
						summary: row.summary,
						color: row.status === 'In Process' ? 'yellow' : 'blue',
					}),
				)
			}
		},
	}
})
</script>
