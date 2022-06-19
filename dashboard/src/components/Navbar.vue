<template>
	<nav class="border-b bg-white">
		<div class="z-10 mx-auto md:container">
			<div class="flex h-16 items-center justify-between px-4 sm:px-8">
				<div class="flex items-center">
					<div class="shrink-0">
						<router-link to="/">
							<FrappeCloudLogo class="h-4 w-auto" />
						</router-link>
					</div>
					<div class="hidden md:block">
						<div class="ml-10 flex items-baseline space-x-4">
							<router-link
								v-for="item in items"
								:key="item.label"
								:to="item.route"
								v-slot="{ href, route, navigate, isActive, isExactActive }"
							>
								<a
									:class="[
										(
											item.highlight
												? item.highlight(route)
												: item.route == '/'
												? isExactActive
												: isActive
										)
											? 'bg-blue-50 text-blue-500'
											: 'text-gray-900 hover:bg-gray-50'
									]"
									:href="href"
									@click="navigate"
									class="rounded-md px-3 py-2 text-sm font-medium focus:outline-none"
								>
									{{ item.label }}
								</a>
							</router-link>
						</div>
					</div>
				</div>
				<div class="hidden md:block">
					<div class="flex items-center">
						<Button icon-left="book-open" link="/docs">Docs</Button>
						<Button class="ml-2" icon-left="life-buoy" link="/support"
							>Support</Button
						>
						<div class="relative ml-3">
							<div>
								<Dropdown :items="dropdownItems" right>
									<template v-slot="{ toggleDropdown }">
										<button
											class="focus:shadow-solid flex max-w-xs items-center rounded-full text-sm text-white focus:outline-none"
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
				<div class="-mr-2 flex md:hidden">
					<button
						class="focus:shadow-outline-gray inline-flex items-center justify-center rounded-md p-2 text-gray-700 focus:outline-none"
						@click="mobileMenuOpen = !mobileMenuOpen"
					>
						<FeatherIcon v-if="!mobileMenuOpen" name="menu" class="h-6 w-6" />
						<FeatherIcon v-else name="x" class="h-6 w-6" />
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
							(item.route == '/' ? isExactActive : isActive)
								? 'bg-blue-50 bg-white text-blue-500'
								: 'text-gray-900 hover:bg-gray-50'
						]"
						:href="href"
						@click="navigate"
						class="block rounded-md px-3 py-2 text-sm font-medium focus:outline-none"
					>
						{{ item.label }}
					</a>
				</router-link>
			</div>
			<div class="border-t pt-4 pb-3">
				<div class="flex items-center px-4">
					<div class="shrink-0">
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
				<div class="mt-3 space-y-3 px-2">
					<a
						href="/support/tickets"
						target="_blank"
						class="block rounded-md px-3 pt-4 text-base font-medium focus:outline-none"
					>
						Support
					</a>
					<a
						href="/docs"
						target="_blank"
						class="block rounded-md px-3 text-base font-medium focus:outline-none"
					>
						Docs
					</a>
					<a
						href="#"
						class="block rounded-md px-3 text-base font-medium focus:outline-none"
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

export default {
	components: {
		FrappeCloudLogo
	},
	data() {
		return {
			mobileMenuOpen: false,
			dropdownItems: [
				{
					label: 'Settings',
					action: () => this.$router.push('/account/profile')
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
