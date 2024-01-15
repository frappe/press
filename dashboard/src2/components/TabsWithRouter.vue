<template>
	<FTabs v-model="currentTab" :tabs="tabs">
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
	data() {
		return {
			currentTab: 0
		};
	},
	watch: {
		currentTab(value) {
			let tab = this.tabs[value];
			if (
				this.$route.name !== tab.routeName &&
				!tab.childrenRoutes?.includes(this.$route.name)
			) {
				this.$router.replace({ name: tab.routeName });
			}
		}
	},
	beforeRouteUpdate(to, from, next) {
		this.setTabToRoute(to);
		next();
	},
	mounted() {
		this.setTabToRoute(this.$route);
	},
	methods: {
		setTabToRoute(route) {
			for (let tab of this.tabs) {
				if (
					route.name === tab.routeName ||
					tab.childrenRoutes?.includes(route.name)
				) {
					this.currentTab = this.tabs.indexOf(tab);
					break;
				}
			}
		}
	}
};
</script>
