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
import router from '../router';

let current;
router.beforeEach((to, from, next) => {
	if (current) {
		current.setTabToRoute(to);
	}
	next();
});

export default {
	name: 'TabsWithRouter',
	props: ['tabs'],
	components: {
		FTabs: Tabs
	},
	data() {
		return {
			currentTab: 0,
			childRoute: null
		};
	},
	watch: {
		currentTab(value) {
			let tab = this.tabs[value];
			let tabRouteName = tab.routeName || tab.route.name;
			if (
				this.$route.name !== tabRouteName &&
				!tab.childrenRoutes?.includes(this.$route.name)
			) {
				// if user comes from tab A to child route of tab B, go to the child route
				if (
					this.childRoute &&
					tab.childrenRoutes?.includes(this.childRoute.name)
				) {
					this.$router.replace({
						name: this.childRoute.name,
						params: this.childRoute.params
					});
				} else this.$router.replace({ name: tabRouteName });
			}
			this.childRoute = null;
		}
	},
	beforeMount() {
		this.setTabToRoute(this.$route);
		current = this;
	},
	beforeUnmount() {
		current = null;
	},
	methods: {
		setTabToRoute(route) {
			for (let tab of this.tabs) {
				let tabRouteName = tab.routeName || tab.route.name;
				if (
					route.name === tabRouteName ||
					tab.childrenRoutes?.includes(route.name)
				) {
					if (tab.childrenRoutes?.includes(route.name)) {
						this.childRoute = route;
					}
					this.currentTab = this.tabs.indexOf(tab);
					break;
				}
			}
		}
	}
};
</script>
