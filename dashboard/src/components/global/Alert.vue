<template>
	<div class="block w-full">
		<div class="flex items-center rounded-md p-3 text-base" :class="classes">
			<FeatherIcon
				v-if="type === 'warning'"
				name="alert-circle"
				class="h-5 w-5 text-ink-gray-9"
			/>
			<div class="ml-2 w-full">
				<div class="flex flex-col md:flex-row md:items-baseline">
					<h3 class="text-lg font-medium text-ink-gray-9" v-if="title">
						{{ title }}
					</h3>
					<div class="mt-1 md:ml-2 md:mt-0">
						<slot></slot>
					</div>
					<div class="mt-3 md:ml-auto md:mt-0">
						<slot name="actions"></slot>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'Alert',
	props: {
		title: String,
		type: {
			type: String,
			default: 'warning',
		},
	},
	computed: {
		classes() {
			return {
				warning: 'text-ink-gray-7 bg-surface-gray-1',
			}[this.type];
		},
	},
};
</script>
