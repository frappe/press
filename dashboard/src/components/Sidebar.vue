<template>
	<div>
		<div class="pt-4 pb-2 px-2 h-full block bg-gray-200 text-sm">
			<Dropdown class="w-full" :items="userDropdownItems">
				<template v-slot="{ toggleDropdown }">
					<div
						@click="toggleDropdown()"
						class="p-3 font-semibold flex items-center cursor-pointer hover:text-gray-600"
					>
						Aditya Hase
						<FeatherIcon name="chevron-down" class="ml-2 w-4 h-4" />
					</div>
				</template>
			</Dropdown>
			<router-link
				v-for="item in items"
				:key="item.label"
				:to="item.route"
				v-slot="{ href, route, navigate, isActive, isExactActive }"
			>
				<a
					class="mt-1 px-3 py-2 flex items-center rounded-lg cursor-pointer hover:bg-white"
					:class="[
						(item.route == '/'
						? isExactActive
						: isActive)
							? 'text-blue-500 bg-white'
							: 'text-gray-900'
					]"
					:href="href"
					@click="navigate"
				>
					{{ item.label }}
				</a>
			</router-link>
		</div>
	</div>
</template>
<script>
export default {
	name: 'Sidebar',
	data() {
		return {
			items: [
				{
					label: 'Dashboard',
					route: '/'
				},
				{
					label: 'Sites',
					route: '/sites'
				}
			],
			userDropdownItems: [
				{
					label: 'Account Settings',
					action: () => {}
				},
				{
					label: 'Logout',
					action: this.$store.auth.logout
				}
			]
		};
	}
};
</script>
