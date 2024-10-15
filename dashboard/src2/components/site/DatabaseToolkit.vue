<template>
	<!-- Buttons -->
	<div class="mx-auto max-w-3xl space-y-4" v-if="!selectedAction">
		<div class="divide-y rounded border border-gray-200 p-5">
			<div class="pb-3 text-lg font-semibold">Database Toolkit</div>
			<DatabaseToolkitButton
				v-for="button in buttonDefinitions"
				:key="button.action"
				:details="button"
				:selectAction="selectAction"
			/>
		</div>
	</div>
	<!-- Screen -->
	<div v-else>
		<div class="mb-5 flex items-center space-x-4">
			<Button @click="goBack" icon="arrow-left" label="Go Back"></Button>
			<h2 class="font-semibold">{{ pageTitle }}</h2>
		</div>
		<!-- Browse Schema Page -->
		<DatabaseBrowseSchema v-if="selectedAction == 'browse-schema'" />
	</div>
</template>
<script>
import { getCachedDocumentResource } from 'frappe-ui';
import DatabaseToolkitButton from './DatabaseToolkitButton.vue';
import { defineAsyncComponent } from 'vue';

export default {
	name: 'DatabaseToolkit',
	props: ['site'],
	components: {
		DatabaseToolkitButton,
		DatabaseBrowseSchema: defineAsyncComponent(() =>
			import('./database/DatabaseBrowseSchema.vue')
		)
	},
	provide() {
		return {
			site: this.site
		};
	},
	data() {
		return {
			selectedAction: null,
			pageTitle: null,
			buttonDefinitions: [
				{
					label: 'Browse Schema',
					description: 'Browse your database schema',
					buttonLabel: 'View',
					action: 'browse-schema'
				}
			]
		};
	},
	methods: {
		selectAction(details) {
			this.selectedAction = details.action;
			this.pageTitle = details.label;
		},
		goBack() {
			this.selectedAction = null;
		}
	}
};
</script>
