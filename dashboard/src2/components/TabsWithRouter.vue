<template>
	<FTabs v-if="visibleTabs?.length" v-model="currentTab" :tabs="visibleTabs">
		<template #default="{ tab }">
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
	props: ['tabs'],
	components: {
		FTabs: Tabs
	},
	computed: {
		visibleTabs() {
			return this.tabs.filter(tab => (tab.condition ? tab.condition() : true));
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
			set(val) {
				let tab = this.visibleTabs[val];
				let tabRouteName = tab.routeName || tab.route.name;
				this.$router.replace({ name: tabRouteName });
			}
		}
	}
};
</script>
