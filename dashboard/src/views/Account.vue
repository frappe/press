<template>
	<div>
		<div class="px-4 sm:px-8" v-if="$account.user">
			<div class="py-8">
				<div class="flex items-center">
					<h1 class="text-2xl font-bold">Account Settings</h1>
					<span class="ml-2 text-gray-600">
						{{ $account.user.name }}
					</span>
				</div>
			</div>
		</div>
		<div class="px-4 sm:px-8">
			<Tabs class="pb-32" :tabs="tabs">
				<router-view
					v-if="$account.user"
					v-bind="{ account: $account }"
				></router-view>
			</Tabs>
		</div>
	</div>
</template>

<script>
import Tabs from '@/components/Tabs';

export default {
	name: 'Account',
	components: {
		Tabs
	},
	data: () => ({
		tabs: [
			{ label: 'Profile', route: 'profile' },
			{ label: 'Team', route: 'team' },
			{ label: 'Billing', route: 'billing' }
		]
	}),
	activated() {
		if (this.$route.matched.length === 1) {
			let path = this.$route.fullPath;
			this.$router.replace(`${path}/profile`);
		}
	},
	beforeRouteUpdate(to, from, next) {
		if (to.path == '/account') {
			next('/account/profile');
		} else {
			next();
		}
	}
};
</script>
