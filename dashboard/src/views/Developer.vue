<template>
	<div class="mt-8">
		<div class="px-4 sm:px-8">
			<div class="pb-3">
				<div>
					<h1 class="text-3xl font-bold">Manage Apps</h1>
				</div>
			</div>
		</div>

		<div class="px-4 sm:px-8">
			<Tabs class="pb-32" :tabs="tabs">
				<router-view v-if="$account.team"></router-view>
			</Tabs>
		</div>
	</div>
</template>

<script>
import Tabs from '@/components/Tabs.vue';

export default {
	name: 'Developer',
	components: {
		Tabs
	},
	data: () => ({
		tabs: [
			{ label: 'My Apps', route: '/developer/apps' },
			{ label: 'Profile', route: '/developer/profile' }
		]
	}),
    activated() {
		if (this.$route.matched.length === 1) {
			let path = this.$route.fullPath;
			this.$router.replace(`${path}/apps`);
		}
	},
	beforeRouteUpdate(to, from, next) {
        console.log(to, from, next);
		if (to.path == '/developer') {
			next('/developer/apps');
		} else {
			next();
		}
	}
};
</script>
