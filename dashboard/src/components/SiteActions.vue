<template>
	<div class="mx-auto max-w-3xl space-y-4" v-if="$site?.doc?.actions">
		<div
			v-for="group in actions"
			:key="group.group"
			class="divide-y rounded border border-outline-gray-1 p-5"
		>
			<div class="pb-3 text-lg font-semibold">{{ group.group }}</div>
			<AlertBanner
				v-if="group.group == 'General Actions'"
				type="warning"
				title="Change Bench / Server / Region options moved to Migrations Tab"
				class="mb-3"
			>
				<Button
					class="ml-auto shrink-0"
					variant="outline"
					@click="openSiteMigrationsDoc"
				>
					View Documentation
				</Button>
			</AlertBanner>
			<!-- Migration shortcuts: deep-link to the Migrations tab with the dialog
			     opened and the right migration type preselected. -->
			<template v-if="$site?.doc?.status !== 'Archived'">
				<div
					class="py-3 first:pt-0 last:pb-0"
					v-for="shortcut in migrationShortcutsFor(group.group)"
					:key="shortcut.action"
				>
					<div class="flex items-center justify-between gap-1">
						<div>
							<h3 class="text-base font-medium">{{ shortcut.label }}</h3>
							<p class="mt-1 text-p-base text-ink-gray-6">
								{{ shortcut.description }}
							</p>
						</div>
						<Button
							class="whitespace-nowrap"
							@click="openMigration(shortcut.action)"
						>
							<p
								:class="
									group.group === 'Dangerous Actions'
										? 'text-red-600'
										: 'text-ink-gray-8'
								"
							>
								{{ shortcut.buttonLabel }}
							</p>
						</Button>
					</div>
				</div>
			</template>
			<div
				class="py-3 first:pt-0 last:pb-0"
				v-for="row in group.actions"
				:key="row.action"
			>
				<SiteActionCell
					:siteName="site"
					:group="group.group"
					:actionLabel="row.action"
					:method="row.doc_method"
					:description="row.description"
					:buttonLabel="row.button_label"
				/>
			</div>
		</div>
	</div>
</template>
<script>
import { getCachedDocumentResource } from 'frappe-ui'
import { defineAsyncComponent, h } from 'vue'
import { renderDialog } from '../utils/components'
import AlertBanner from './AlertBanner.vue'
import SiteActionCell from './SiteActionCell.vue'

export default {
	name: 'SiteActions',
	props: ['site'],
	components: { SiteActionCell, AlertBanner },
	data() {
		return {
			// `action` matches the keys returned by Site.get_migration_options, which
			// the migration dialog uses to preselect the migration type. `group`
			// places the shortcut under the matching site action section.
			migrationShortcuts: [
				{
					label: 'In-Place Migrate Site',
					action: 'In-Place Migrate Site',
					description:
						'Run bench migrate on the current bench to apply pending patches and schema changes.',
					buttonLabel: 'Migrate Site',
					group: 'Dangerous Actions',
				},
				{
					// A site on a shared bench moves off it; a site on a private bench
					// moves between its own benches and servers.
					label: (site) =>
						site.group_public
							? 'Move to a Private Bench'
							: 'Move to a Different Bench or Server',
					action: 'Move Site To Different Server / Bench',
					description: (site) =>
						site.group_public
							? 'Leave the shared bench. You choose the bench and the server, and you decide when it updates.'
							: 'Move this site to another of your benches, or to one of your other servers.',
					buttonLabel: 'Choose Bench',
					group: 'General Actions',
				},
				{
					label: 'Move to Another Shared Server',
					action: 'Move Site To Another Shared Server',
					// The dialog carries the rest: the server we picked and the 60-day limit
					description:
						'Stay on shared hosting, on a quieter machine in the same region.',
					buttonLabel: 'Move Site',
					group: 'General Actions',
					condition: (site) => !site.is_dedicated_server,
				},
				{
					label: 'Move to a Different Region',
					action: 'Move Site To Different Region',
					description: 'Move this site to a bench in another region.',
					buttonLabel: 'Move Site',
					group: 'General Actions',
				},
			],
		}
	},
	computed: {
		$site() {
			return getCachedDocumentResource('Site', this.site)
		},
		actions() {
			const groupedActions = this.$site.doc.actions.reduce((acc, action) => {
				const group = action.group || 'General Actions'
				if (!acc[group]) {
					acc[group] = []
				}
				acc[group].push(action)
				return acc
			}, {})

			return Object.keys(groupedActions).map((group) => ({
				group,
				actions: groupedActions[group],
			}))
		},
	},
	methods: {
		migrationShortcutsFor(group) {
			return this.migrationShortcuts
				.filter(
					(shortcut) =>
						shortcut.group === group &&
						(!shortcut.condition || shortcut.condition(this.$site.doc)),
				)
				.map((shortcut) => ({
					...shortcut,
					label: this.textForSite(shortcut.label),
					description: this.textForSite(shortcut.description),
				}))
		},
		textForSite(text) {
			// A label or description can depend on the site it is shown for
			return typeof text === 'function' ? text(this.$site.doc) : text
		},
		openSiteMigrationsDoc() {
			window.open(
				'https://docs.frappe.io/cloud/site/site-migrations/introduction-to-site-migration',
				'_blank',
			)
		},
		openMigration(action) {
			// Land the user on the Migrations tab, then open the migration dialog
			// with the chosen migration type preselected.
			this.$router
				.push({
					name: 'Site Detail Migrations',
					params: { name: this.site },
				})
				.then(() => {
					renderDialog(
						h(
							defineAsyncComponent(() => import('./site/SiteMigration.vue')),
							{ site: this.site, defaultAction: action },
						),
					)
				})
		},
	},
}
</script>
