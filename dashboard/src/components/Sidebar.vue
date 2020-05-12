<template>
	<div>
		<div
			class="flex flex-col justify-between block h-full px-2 pb-2 text-sm bg-gray-100"
		>
			<div>
				<div class="flex px-2 py-4">
					<router-link class="text-lg font-bold" :to="'/'">
						Frappe Cloud
					</router-link>
				</div>
				<router-link
					v-for="item in items"
					:key="item.label"
					:to="item.route"
					v-slot="{ href, route, navigate, isActive, isExactActive }"
				>
					<a
						class="flex items-center px-3 py-2 mt-1 rounded-lg cursor-pointer hover:bg-white"
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
			<router-link
				v-if="$store.account.user"
				to="/account"
				v-slot="{ href, route, navigate, isActive }"
			>
				<a
					class="inline-flex items-start px-2 py-3 rounded-md"
					:class="isActive ? 'bg-white' : 'hover:bg-gray-300'"
					:href="href"
				>
					<Avatar
						:label="$store.account.user.first_name"
						:imageURL="$store.account.user.user_image"
					/>
					<div class="ml-2">
						<div class="font-semibold">
							{{ $store.account.user.first_name }}
							{{ $store.account.user.last_name }}
						</div>
						<div class="text-xs" @click.prevent="$store.auth.logout">
							Logout
						</div>
					</div>
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
					label: 'Sites',
					route: '/sites'
				},
				{
					label: 'Support',
					route: '/support'
				}
			]
		};
	}
};
</script>
