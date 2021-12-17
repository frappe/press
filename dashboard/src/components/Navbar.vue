<template>
	<nav class="bg-white border-b">
		<div class="container z-10 mx-auto">
			<div class="flex items-center justify-between h-16 px-4 sm:px-8">
				<div class="flex items-center">
					<div class="flex-shrink-0">
						<router-link to="/">
							<FrappeCloudLogo class="w-auto h-4" />
						</router-link>
					</div>
					<div class="hidden md:block">
						<div class="flex items-baseline ml-10 space-x-4">
							<router-link
								v-for="item in items"
								:key="item.label"
								:to="item.route"
								v-slot="{ href, route, navigate, isActive, isExactActive }"
							>
								<a
									:class="[
										(item.highlight
										? item.highlight(route)
										: item.route == '/'
										? isExactActive
										: isActive)
											? 'bg-blue-50 text-blue-500'
											: 'text-gray-900 hover:bg-gray-50'
									]"
									:href="href"
									@click="navigate"
									class="px-3 py-2 text-sm font-medium rounded-md focus:outline-none"
								>
									{{ item.label }}
								</a>
							</router-link>
						</div>
					</div>
				</div>
				<div class="hidden md:block">
					<div class="flex items-center">
						<SiteAndBenchSearch class="mr-5" />
						<Button icon-left="life-buoy" link="/support">Support</Button>
						<div class="relative ml-3">
							<div>
								<Dropdown :items="dropdownItems" right>
									<template v-slot="{ toggleDropdown }">
										<button
											class="flex items-center max-w-xs text-sm text-white rounded-full focus:outline-none focus:shadow-solid"
											id="user-menu"
											aria-label="User menu"
											aria-haspopup="true"
											@click="toggleDropdown()"
										>
											<Avatar
												v-if="$account.user"
												:label="$account.user.first_name"
												:imageURL="$account.user.user_image"
											/>
										</button>
									</template>
								</Dropdown>
							</div>
						</div>
					</div>
				</div>
				<div class="flex -mr-2 md:hidden">
					<button
						class="inline-flex items-center justify-center p-2 text-gray-700 rounded-md focus:outline-none focus:shadow-outline-gray"
						@click="mobileMenuOpen = !mobileMenuOpen"
					>
						<FeatherIcon v-if="!mobileMenuOpen" name="menu" class="w-6 h-6" />
						<FeatherIcon v-else name="x" class="w-6 h-6" />
					</button>
				</div>
			</div>
		</div>
		<div class="md:hidden" :class="mobileMenuOpen ? 'block' : 'hidden'">
			<div class="px-4 pb-2">
				<router-link
					v-for="item in items"
					:key="item.label"
					:to="item.route"
					v-slot="{ href, route, navigate, isActive, isExactActive }"
				>
					<a
						:class="[
							(item.route == '/'
							? isExactActive
							: isActive)
								? 'bg-blue-50 text-blue-500 bg-white'
								: 'text-gray-900 hover:bg-gray-50'
						]"
						:href="href"
						@click="navigate"
						class="block px-3 py-2 text-sm font-medium rounded-md focus:outline-none"
					>
						{{ item.label }}
					</a>
				</router-link>
			</div>
			<div class="pt-4 pb-3 border-t">
				<div class="flex items-center px-4">
					<div class="flex-shrink-0">
						<Avatar
							v-if="$account.user"
							:label="$account.user.first_name"
							:imageURL="$account.user.user_image"
						/>
					</div>
					<div class="ml-3" v-if="$account.user">
						<div class="text-base font-medium leading-none">
							{{ $account.user.first_name }} {{ $account.user.last_name }}
						</div>
						<div class="mt-1 text-sm font-medium leading-none text-gray-400">
							{{ $account.user.email }}
						</div>
					</div>
				</div>
				<div class="px-2 mt-3 space-y-3">
					<a
						href="/support/tickets"
						target="_blank"
						class="block px-3 pt-4 text-base font-medium rounded-md focus:outline-none"
					>
						Support
					</a>
					<a
						href="#"
						class="block px-3 text-base font-medium rounded-md focus:outline-none"
						@click.prevent="$auth.logout"
					>
						Logout
					</a>
				</div>
			</div>
		</div>
	</nav>
</template>

<script>
import FrappeCloudLogo from '@/components/FrappeCloudLogo.vue';
import SiteAndBenchSearch from '@/components/SiteAndBenchSearch.vue';

export default {
	components: {
		FrappeCloudLogo,
		SiteAndBenchSearch
	},
	data() {
		return {
			mobileMenuOpen: false,
			dropdownItems: [
				{
					label: 'New Bench',
					action: () => this.$router.push('/benches/new')
				},
				{
					label: 'Settings',
					action: () => this.$router.push('/account')
				},
				{
					label: 'Support',
					action: () => window.open('/support/tickets', '_blank')
				},
				{
					label: 'Logout',
					action: () => this.$auth.logout()
				}
			]
		};
	},
	computed: {
		items() {
			return [
				{
					label: 'Dashboard',
					route: '/sites',
					highlight: () => {
						return this.$route.fullPath.endsWith('/sites');
					}
				},
				{
					label: 'My Apps',
					route: '/marketplace',
					highlight: () => {
						return this.$route.fullPath.includes('/marketplace');
					},
					condition: () => this.$account.team?.is_developer
				},
				{
					label: 'Settings',
					route: '/account'
				}
			].filter(d => (d.condition ? d.condition() : true));
		}
	}
};
</script>
