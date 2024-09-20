<template>
	<div class="m-5">
		<div class="flex items-center space-x-4">
			<Button @click="goBack" icon="arrow-left" label="Go Back" />
			<h2 class="font-semibold">{{ title }}</h2>
		</div>
		<div v-if="$site.doc?.current_plan?.monitor_access" class="mt-5">
			<ObjectList :options="reportOptions" />
		</div>
		<div class="flex justify-center" v-else>
			<span class="mt-16 p-2 text-base text-gray-800">
				Your plan doesn't support this feature. Please
				<span class="cursor-pointer underline" @click="showPlanChangeDialog"
					>upgrade your plan</span
				>
				.
			</span>
		</div>
	</div>
</template>

<script>
import { getCachedDocumentResource } from 'frappe-ui';
import { defineAsyncComponent, h } from 'vue';
import { renderDialog } from '../../../utils/components';
import ObjectList from '../../ObjectList.vue';

export default {
	name: 'PerformanceReport',
	props: {
		title: {
			type: String,
			required: true
		},
		site: {
			type: String,
			required: true
		},
		reportOptions: {
			type: Object,
			required: true
		}
	},
	components: {
		ObjectList
	},
	computed: {
		$site() {
			return getCachedDocumentResource('Site', this.site);
		}
	},
	methods: {
		showPlanChangeDialog() {
			const SitePlansDialog = defineAsyncComponent(() =>
				import('../../ManageSitePlansDialog.vue')
			);
			renderDialog(h(SitePlansDialog, { site: this.site }));
		},
		goBack() {
			this.$router.go(-1);
		}
	}
};
</script>
