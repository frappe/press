import { frappeRequest } from 'frappe-ui'

const pollingGroups = new Set()

export function pollReleasePipelineValidationStatus(group) {
	if (pollingGroups.has(group.doc.name)) return // already polling
	if (!group.doc.deploy_information.has_running_release_pipeline) return

	pollingGroups.add(group.doc.name)

	function poll() {
		frappeRequest({
			url: 'press.api.bench.deploy_status',
			params: { name: group.name },
		})
			.then(({ is_validating, is_deploy_in_progress, candidate }) => {
				if (!group.doc.deploy_information.has_running_release_pipeline) {
					pollingGroups.delete(group.doc.name)
					return
				}

				group.doc.deploy_information.deploy_in_progress = Boolean(
					is_deploy_in_progress,
				)

				if (candidate) {
					group.doc.deploy_information.last_deploy = {
						name: candidate,
					}
				}

				if (is_validating || is_deploy_in_progress) {
					group.doc.status = 'Deploying'
					setTimeout(poll, 2000) // still validating or building, keep polling
				} else {
					// Deploy finished (idle)
					group
						.reload()
						.then(() => {
							pollingGroups.delete(group.doc.name)
							if (group.doc.deploy_information.has_running_release_pipeline) {
								pollReleasePipelineValidationStatus(group)
							}
						})
						.catch(() => {
							pollingGroups.delete(group.doc.name)
						})
				}
			})
			.catch(() => {
				pollingGroups.delete(group.doc.name)
			})
	}

	poll()
}
