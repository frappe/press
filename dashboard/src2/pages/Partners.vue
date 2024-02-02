<template>
	<div class="sticky top-0 z-10 shrink-0">
		<Header>
			<FBreadcrumbs
				:items="[{ label: 'Partners', route: { name: 'Partners' } }]"
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
	name: 'Partner',
	components: {
		Header,
		FBreadcrumbs: Breadcrumbs,
		FTabs: Tabs,
		TabsWithRouter
	},
	data() {
		return {
			currentTab: 0,
			tabs: [
				{ label: 'Overview', route: { name: 'PartnerOverview' } },
				{ label: 'Customers', route: { name: 'PartnerCustomers' } },
				{
					label: 'Approval Requests',
					route: { name: 'PartnerApprovalRequests' }
				}
			]
		};
	}
};
</script>
