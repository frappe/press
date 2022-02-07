<template>
	<div>
		<div
			class="block flex h-full flex-col justify-between bg-gray-100 px-2 pb-2 text-sm"
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
						class="mt-1 flex cursor-pointer items-center rounded-lg px-3 py-2 hover:bg-white"
						:class="[
							(item.route == '/' ? isExactActive : isActive)
								? 'bg-white text-blue-500'
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
				v-if="$account.user"
				to="/account"
				v-slot="{ href, route, navigate, isActive }"
			>
				<a
					class="inline-flex items-start rounded-md px-2 py-3"
					:class="isActive ? 'bg-white' : 'hover:bg-gray-300'"
					:href="href"
				>
					<Avatar
						:label="$account.user.first_name"
						:imageURL="$account.user.user_image"
					/>
					<div class="ml-2">
						<div class="font-semibold">
							{{ $account.user.first_name }}
							{{ $account.user.last_name }}
						</div>
						<div class="text-xs" @click.prevent="$auth.logout">Logout</div>
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
