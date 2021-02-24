<template>
	<div class="mt-8">
		<div class="px-4 sm:px-8" v-if="$account.user">
			<div class="pb-3">
				<div>
					<h1 class="text-3xl font-bold">Settings</h1>
					<div class="mt-2 text-base text-gray-600">
						<span>
							{{ $account.user.name }}
						</span>
						<template v-if="$account.team.erpnext_partner">
							&middot;
							<span>ERPNext Partner</span>
						</template>
						&middot;
						<span>
							Member since
							{{
								$date($account.team.creation).toLocaleString({
									month: 'short',
									day: 'numeric'
								})
							}}
						</span>
					</div>
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
			{ label: 'Profile', route: '/account/profile' },
			{ label: 'Team', route: '/account/team' },
			{ label: 'Billing', route: '/account/billing' }
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
