<template>
	<div class="mt-8">
		<div class="px-4 sm:px-8">
			<div class="pb-3">
				<div class="flex items-center justify-between">
					<h1 class="text-3xl font-bold">Manage Apps</h1>
					<Button
						type="primary"
						iconLeft="plus"
						@click="showAppCreationDialog = true"
					>
						Create App
					</Button>
				</div>
			</div>
		</div>

		<Dialog
			title="Want to submit another app?"
			:dismissable="true"
			v-model="showAppCreationDialog"
		>
			<p class="text-lg">
				Please
				<a
					class="text-blue-500 hover:text-blue-700"
					href="/support/tickets"
					target="_blank"
					>raise a support ticket</a
				>
				with the necessary information to submit an app to marketplace. We will
				guide you from there!
			</p>
		</Dialog>

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
		],
		showAppCreationDialog: false
	}),
	activated() {
		if (this.$route.matched.length === 1) {
			let path = this.$route.fullPath;
			this.$router.replace(`${path}/apps`);
		}
	},
	beforeRouteUpdate(to, from, next) {
		if (to.path == '/developer') {
			next('/developer/apps');
		} else {
			next();
		}
	}
};
</script>
