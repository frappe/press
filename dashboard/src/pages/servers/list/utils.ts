import { createDocumentResource } from 'frappe-ui'
import { toast } from 'vue-sonner'
import { confirmDialog } from '@/utils/components'
import router from '@/router'

export function dropBench(bench: any) {
  const releaseGroup = createDocumentResource({
    doctype: 'Release Group',
    name: bench.name,
  })

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

export const onDropServer = (server: any) => {
	const serverFullRes = createDocumentResource({
		doctype: 'Server',
		name: server.name,
	})

	confirmDialog({
		title: 'Drop Server',
		message: server.is_unified_server
			? `<div class="prose text-base">Are you sure you want to drop your unified server?<br><br>The following server will be dropped<ul><li>${server.title} (<b>${server.name}</b>)</li></ul><br>This action cannot be undone.</div>`
			: `<div class="prose text-base">Are you sure you want to drop your servers?<br><br>Following servers will be dropped<ul><li>${server.title} (<b>${server.name}</b>)</li><li>${server.database_server}</li></ul><br>This action cannot be undone.</div>`,
		fields: [
			{
				label: "Please type either server's name or title to confirm",
				fieldname: 'confirmServerName',
			},
		],
		primaryAction: {
			label: 'Drop Server',
			theme: 'red',
		},
		onSuccess({ hide, values }) {
			if (serverFullRes.dropServer.loading) return
			const confirmed = values.confirmServerName
			if (
				confirmed !== server.name &&
				confirmed !== server.database_server &&
				confirmed.trim() !== server.title.trim()
			) {
				throw new Error('Server name does not match')
			}
			toast.promise(serverFullRes.dropServer.submit().then(hide), {
				loading: 'Dropping...',
				success: () => {
					router.push({ name: 'Server List' })
					return 'Server dropped'
				},
				error: (error) =>
					error.messages.length
						? error.messages.join('\n')
						: 'Failed to drop servers',
			})
		},
	})
}
