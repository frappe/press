<template>
	<FTabs v-model="currentTab" :tabs="tabs">
		<template #default="{ tab }">
			<router-view :tab="tab" />
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
			this.$router.replace(tab.route);
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
				if (route.name === tab.route.name) {
					this.currentTab = this.tabs.indexOf(tab);
					break;
				}
			}
		}
	}
};
</script>
