import { createListResource, createResource } from 'frappe-ui'
import { computed } from 'vue'
import { getTeam } from '../../data/team'

const team = getTeam()

const sites = createListResource({
	doctype: 'Site',
	auto: true,
	fields: ['name', 'host_name'],
	pageLength: 99999,
	filters: {
		team: team.doc?.name,
	},
})

const servers = createListResource({
	doctype: 'Server',
	auto: true,
	fields: ['name', 'title'],
	pageLength: 99999,
	filters: {
		team: team.doc?.name,
	},
})

const releaseGroups = createListResource({
	doctype: 'Release Group',
	auto: true,
	fields: ['name', 'title'],
	pageLength: 99999,
	filters: {
		team: team.doc?.name,
	},
})

export const teamMembers = (ignore: string[] = []) => {
	return team.doc?.team_members
		.filter((u: any) => !ignore.some((user) => user === u.user))
		.map((user: any) => ({
			label: user.user,
			value: user.user,
		}))
}

// Titles are not unique. Two benches can share one, and the native select of
// the create dialog has no room for a second line, so the name goes inline.
const resourceLabel = (title: string, name: string) =>
	title && title !== name ? `${title} (${name})` : name

export const teamResources = computed(() => {
	const r: {
		document_type: string
		document_name: string
		label: string
		value: string
	}[] = []
	if (sites.data) {
		r.push(
			...sites.data.map((site: any) => ({
				document_type: 'Site',
				document_name: site.name,
				label: resourceLabel(site.host_name, site.name),
				value: site.name,
			})),
		)
	}
	if (servers.data) {
		r.push(
			...servers.data.map((server: any) => ({
				document_type: 'Server',
				document_name: server.name,
				label: resourceLabel(server.title, server.name),
				value: server.name,
			})),
		)
	}
	if (releaseGroups.data) {
		r.push(
			...releaseGroups.data.map((rg: any) => ({
				document_type: 'Release Group',
				document_name: rg.name,
				label: resourceLabel(rg.title, rg.name),
				value: rg.name,
			})),
		)
	}
	return r
})

// Not a doctype: Press Role stores these in its `repositories` table
export const REPOSITORY = 'GitHub Repository'

const fetchResource = (url: string, params = {}) =>
	createResource({ url, params }).fetch()

// One request per GitHub account, in parallel. An account GitHub refuses is skipped.
export const fetchTeamRepositories = async () => {
	const options = await fetchResource('press.api.github.options')
	const lists = await Promise.all(
		(options?.installations || []).map(async (installation: any) => {
			const repositories = await fetchResource(
				'press.api.github.installation_repositories',
				{ installation: String(installation.id) },
			).catch(() => [])
			return (repositories || []).map((repository: any) => {
				const name = `${installation.login}/${repository.name}`
				return {
					document_type: REPOSITORY,
					document_name: name,
					label: name,
					value: name,
				}
			})
		}),
	)
	return lists.flat()
}
