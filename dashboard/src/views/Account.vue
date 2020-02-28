<template>
	<div>
		<PageHeader>
			<template slot="title">
				<div class="flex items-center">
					<router-link to="/" class="flex items-center">
						<FeatherIcon name="arrow-left" class="w-4 h-4" />
						<span class="ml-2 text-base">Back</span>
					</router-link>
				</div>
			</template>
		</PageHeader>
		<div class="px-4 sm:px-8" v-if="account.user">
			<div class="border-t"></div>
			<div class="py-8">
				<div class="flex items-center">
					<h1 class="font-medium text-2xl">Account</h1>
					<span class="ml-2 text-gray-600">
						{{ account.user.name }}
					</span>
				</div>
			</div>
		</div>
		<div class="px-4 sm:px-8">
			<div>
				<ul class="hidden sm:flex rounded overflow-hidden text-sm border-b">
					<router-link
						v-for="tab in tabs"
						:key="tab.label"
						:to="tab.route"
						v-slot="{ href, route, navigate, isActive, isExactActive }"
					>
						<li>
							<a
								class="mr-8 px-1 py-4 border-b-2 border-transparent font-medium leading-none block focus:outline-none"
								:class="[
									isExactActive
										? 'border-brand text-brand'
										: 'text-gray-800 hover:text-gray-900'
								]"
								:href="href"
								@click="navigate"
							>
								{{ tab.label }}
							</a>
						</li>
					</router-link>
				</ul>
				<select
					class="block sm:hidden form-select w-full"
					@change="e => changeTab(e.target.value)"
				>
					<option
						v-for="tab in tabs"
						:selected="isTabSelected(tab)"
						:value="tab.route"
					>
						{{ tab.label }}
					</option>
				</select>
			</div>
			<div class="w-full pt-6 sm:pt-10 pb-32" v-if="account.user">
				<router-view v-bind="{ account }"></router-view>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'Account',
	data: () => ({
		tabs: [
			{ label: 'Profile', route: 'profile' },
			{ label: 'Team', route: 'team' },
			{ label: 'Billing', route: 'billing' }
		]
	}),
	async mounted() {
		if (this.$route.matched.length === 1) {
			let path = this.$route.fullPath;
			this.$router.replace(`${path}/profile`);
		}
	},
	methods: {
		isTabSelected(tab) {
			return this.$route.path.endsWith(tab.route);
		},
		changeTab(route) {
			this.$router.push(route);
		}
	},
	computed: {
		account() {
			return this.$store.account;
		}
	}
};
</script>
