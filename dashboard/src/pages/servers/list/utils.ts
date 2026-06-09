import { getCachedDocumentResource } from 'frappe-ui'
import { toast } from 'vue-sonner'
import { confirmDialog } from '@/utils/components'
import router from '@/router'

import HetnzerLogo from '@/logo/Hetzner.vue'
import FrappeLogo from '@/logo/Frappe.vue'
import AwsLogo from '@/logo/Aws.vue'
import OracleLogo from '@/logo/Oracle.vue'
import DigitalOceanLogo from '@/logo/DigitalOcean.vue'


export const providerIcons = {
	'Frappe Compute': FrappeLogo,
	Generic: FrappeLogo,
	Hetzner: HetnzerLogo,
	'AWS EC2': AwsLogo,
	Oracle: OracleLogo,
	DigitalOcean: DigitalOceanLogo,
}

export function dropBench(bench: any) {
	const releaseGroup = getCachedDocumentResource('Release Group', bench.name)

	confirmDialog({
		title: 'Drop Bench',
		message: `Are you sure you want to drop the bench <b>${bench.title}</b>?`,
		fields: [
			{
				label: 'Please type the bench name to confirm',
				fieldname: 'confirmBenchName',
			},
		],
		primaryAction: {
			label: 'Drop',
			theme: 'red',
			onClick: ({ hide, values }) => {
				if (releaseGroup.delete.loading) return
				if (values.confirmBenchName !== bench.title) {
					throw new Error('Bench name does not match')
				}
				toast.promise(
					releaseGroup.delete.submit(null, {
						onSuccess: () => {
							hide()
							router.push({ name: 'Release Group List' })
						},
					}),
					{
						loading: 'Dropping bench...',
						success: 'Bench dropped successfully',
						error: (error) =>
							error.messages?.length
								? error.messages.join('\n')
								: 'Failed to drop bench',
					},
				)
			},
		},
	})
}
