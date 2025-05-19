<template>
	<div class="sticky top-0 z-10 shrink-0">
		<Header>
			<FBreadcrumbs
				:items="[{ label: 'Partner Lead', route: { name: 'PartnerLeads' } }]"
			/>
		</Header>
		<TabsWithRouter :tabs="tabs" />
	</div>
</template>
<script>
import Header from '../components/Header.vue';
import { Breadcrumbs, Tabs } from 'frappe-ui';
import TabsWithRouter from '../components/TabsWithRouter.vue';
export default {
	name: 'PartnerLeadDetails',
	components: {
		Header,
		FBreadcrumbs: Breadcrumbs,
		FTabs: Tabs,
		TabsWithRouter,
	},
	resources: {
		lead() {
			return {
				type: 'document',
				doctype: 'Partner Lead',
				name: this.$route.params.leadId,
			};
		},
	},
	data() {
		return {
			currentTab: 0,
			tabs: [
				{ label: 'Overview', route: { name: 'LeadOverview' } },
				{ label: 'Deal Details', route: { name: 'LeadDealDetails' } },
				{ label: 'Follow Up', route: { name: 'LeadFollowUp' } },
			],
		};
	},
	computed: {
		lead() {
			return this.$resources.lead;
		},
	},
	methods: {},
};
</script>
