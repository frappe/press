<template>
	<div class="inline-block">
		<div
			class="items-start px-4 py-3 text-sm border rounded-md sm:flex"
			:class="classes"
		>
			<FeatherIcon :name="icon" class="w-4 h-4 my-1 mr-2" />
			<div class="my-0.5">
				<slot></slot>
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
			default: 'warning'
		}
	},
	computed: {
		classes() {
			return {
				warning: 'text-orange-700 bg-orange-100 border-orange-300'
			}[this.type];
		},
		icon() {
			return {
				warning: 'alert-circle'
			}[this.type];
		}
	}
};
</script>
