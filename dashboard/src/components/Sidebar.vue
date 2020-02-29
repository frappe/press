<template>
	<div>
		<div
			class="pb-2 px-2 flex flex-col justify-between h-full block bg-gray-200 text-sm"
		>
			<div>
				<div class="flex py-4 px-2">
					<svg
						class="w-6 h-6"
						viewBox="0 0 956 941"
						fill="none"
						xmlns="http://www.w3.org/2000/svg"
					>
						<path
							d="M909.491 851.754H468.772C258.897 851.754 87.321 680.178 87.321 470.303C87.321 260.429 258.897 88.852 468.772 88.852C583.666 88.852 690.902 137.874 765.966 228.258C781.286 246.641 810.392 249.705 828.775 234.386C847.159 219.066 850.223 189.96 834.903 171.576C744.519 62.809 612.773 0 471.835 0C209.875 0 0 212.939 0 470.303C0 727.668 212.939 940.606 470.303 940.606H911.023C935.534 940.606 955.449 922.223 955.449 896.18C955.449 870.137 934.002 851.754 909.491 851.754Z"
							fill="#4794E9"
						/>
						<path
							d="M226.852 470.961C226.852 337.683 335.62 227.384 470.429 227.384C542.43 227.384 611.367 259.555 657.325 314.704C672.644 333.087 701.751 336.151 720.134 320.832C738.518 305.513 741.581 276.406 726.262 258.023C663.453 181.426 570.005 137 470.429 137C286.598 137 138 285.597 138 469.429C138 653.261 286.598 801.858 470.429 801.858H811.574C836.084 801.858 856 783.475 856 757.432C856 731.39 837.616 713.006 811.574 713.006H468.898C335.62 714.538 226.852 604.239 226.852 470.961Z"
							fill="#8CC0F1"
						/>
					</svg>
					<div class="ml-2 font-bold text-lg">Frappe Cloud</div>
				</div>
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
			<router-link
				v-if="$store.account.user"
				to="/account"
				v-slot="{ href, route, navigate, isActive, isExactActive }"
			>
				<a
					class="inline-flex items-start rounded-md px-2 py-3"
					:class="isActive ? 'bg-white' : 'hover:bg-gray-300'"
					:href="href"
				>
					<Avatar
						:label="$store.account.user.first_name"
						:imageURL="$store.account.user.image"
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
				}
			]
		};
	}
};
</script>
