<template>
	<div class="mx-auto max-w-3xl space-y-4" v-if="$site?.doc?.actions">
		<div
			v-for="group in actions"
			:key="group.group"
			class="divide-y rounded border border-gray-200 p-5"
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
import { getCachedDocumentResource } from 'frappe-ui';
import SiteActionCell from './SiteActionCell.vue';
import AlertBanner from './AlertBanner.vue';

export default {
	name: 'SiteActions',
	props: ['site'],
	components: { SiteActionCell, AlertBanner },
	computed: {
		$site() {
			return getCachedDocumentResource('Site', this.site);
		},
		actions() {
			const groupedActions = this.$site.doc.actions.reduce((acc, action) => {
				const group = action.group || 'General Actions';
				if (!acc[group]) {
					acc[group] = [];
				}
				acc[group].push(action);
				return acc;
			}, {});

			return Object.keys(groupedActions).map((group) => ({
				group,
				actions: groupedActions[group],
			}));
		},
	},
	methods: {
		openSiteMigrationsDoc() {
			window.open(
				'https://docs.frappe.io/cloud/site/site-migrations/introduction-to-site-migration',
				'_blank',
			);
		},
	},
};
</script>
