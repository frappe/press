<template>
	<FTabs v-if="visibleTabs?.length" v-model="currentTab" :tabs="visibleTabs">
		<!-- TAB BUTTONS -->
    <template #tab-item="{ tab, selected }">
			<slot name="tab-item" :tab="tab" :selected="selected" />
    </template>
		
		<!-- TAB CONTENT -->
    <template #tab-panel="{ tab }">
			<slot name="tab-content" :tab="tab">
				<router-view :tab="tab" />
			</slot>
    </template>
	</FTabs>
</template>
<script>
import { Tabs } from 'frappe-ui';

export default {
	name: 'TabsWithRouter',
	props: ['tabs', 'document'],
	components: {
		FTabs: Tabs,
	},
	computed: {
		visibleTabs() {
			return this.tabs.filter((tab) => {
				if (
					this.document?.tabs_access &&
					tab.label in this.document.tabs_access &&
					!this.document.tabs_access[tab.label]
				) {
					return false;
				} else if (tab.condition) {
					return tab.condition({ doc: this.document });
				} else {
					return true;
				}
			});
		},
		currentTab: {
			get() {
				for (let tab of this.visibleTabs) {
					let tabRouteName = tab.routeName || tab.route.name;
					if (
						this.$route.name === tabRouteName ||
						tab.childrenRoutes?.includes(this.$route.name)
					) {
						return this.visibleTabs.indexOf(tab);
					}
				}
				return 0;
			},
			set(value) {
				const tab = this.visibleTabs[value];
				if (tab.route) {
					this.$router.push(tab.route);
				}
			}
		},
	},
};
</script>
