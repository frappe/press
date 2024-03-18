<template>
	<FTabs v-if="tabs?.length" v-model="currentTab" :tabs="tabs">
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
		currentTab: {
			get() {
				for (let tab of this.tabs) {
					let tabRouteName = tab.routeName || tab.route.name;
					if (
						this.$route.name === tabRouteName ||
						tab.childrenRoutes?.includes(this.$route.name)
					) {
						return this.tabs.indexOf(tab);
					}
				}
				return 0;
			},
			set(val) {
				let tab = this.tabs[val];
				let tabRouteName = tab.routeName || tab.route.name;
				this.$router.replace({ name: tabRouteName });
			}
		}
	}
};
</script>
