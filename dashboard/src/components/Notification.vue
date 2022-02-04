<template>
	<div
		class="w-full max-w-sm bg-white rounded-lg shadow-lg pointer-events-auto"
	>
		<div class="overflow-hidden rounded-lg shadow-xs">
			<div class="p-4">
				<div class="flex items-start">
					<div class="shrink-0 mr-3" v-if="icon">
						<div class="w-6 h-6 p-1 rounded-full" :class="iconContainerClass">
							<FeatherIcon :name="icon" :class="iconClass" class="w-4 h-4" />
						</div>
					</div>
					<div class="flex-1">
						<p class="text-sm font-medium leading-6 text-gray-900">
							{{ title }}
						</p>
						<p v-if="message" class="mt-1 text-sm leading-5 text-gray-700">
							{{ message }}
						</p>
					</div>
					<div class="flex items-center shrink-0 h-6 ml-3">
						<button @click="$emit('dismiss', id)" class="focus:outline-none">
							<FeatherIcon name="x" class="w-5 h-5 text-gray-800" />
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'Notification',
	props: ['id', 'title', 'message', 'color', 'icon'],
	computed: {
		iconClass() {
			return {
				red: 'text-red-500',
				green: 'text-green-500',
				yellow: 'text-yellow-500',
				blue: 'text-blue-500',
				gray: 'text-gray-500'
			}[this.color || 'gray'];
		},
		iconContainerClass() {
			return {
				red: 'bg-red-100',
				green: 'bg-green-100',
				yellow: 'bg-yellow-100',
				blue: 'bg-blue-100',
				gray: 'bg-gray-100'
			}[this.color || 'gray'];
		}
	}
};
</script>
