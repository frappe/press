<template>
	<div class="mx-auto max-w-3xl space-y-4" v-if="$releaseGroup?.doc?.actions">
		<div
			v-for="group in actions"
			:key="group.group"
			class="divide-y rounded border border-gray-200 p-5"
		>
			<div class="pb-3 text-lg font-semibold">{{ group.group }}</div>
			<div
				class="py-3 first:pt-0 last:pb-0"
				v-for="row in group.actions"
				:key="row.action"
			>
				<ReleaseGroupActionCell
					:benchName="releaseGroup"
					:group="group.group"
					:actionLabel="row.action"
					:method="row.doc_method"
					:description="row.description"
					:buttonLabel="row.button_label"
					:linkedVersionUpgrade="$releaseGroup?.doc?.linked_version_upgrade"
				/>
			</div>
		</div>
	</div>
</template>
<script>
import { getCachedDocumentResource } from 'frappe-ui';
import ReleaseGroupActionCell from './ReleaseGroupActionCell.vue';

export default {
	props: ['releaseGroup'],
	components: { ReleaseGroupActionCell },
	computed: {
		$releaseGroup() {
			return getCachedDocumentResource('Release Group', this.releaseGroup);
		},
		actions() {
			const groupedActions = this.$releaseGroup.doc.actions.reduce(
				(acc, action) => {
					const group = action.group || 'General Actions';
					if (!acc[group]) {
						acc[group] = [];
					}
					acc[group].push(action);
					return acc;
				},
				{},
			);

			return Object.keys(groupedActions).map((group) => ({
				group,
				actions: groupedActions[group],
			}));
		},
	},
};
</script>
