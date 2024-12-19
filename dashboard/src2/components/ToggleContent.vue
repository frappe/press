<template>
	<div class="rounded border text-base">
		<div
			class="flex cursor-pointer select-none flex-row items-center gap-2 p-4"
			@click="toggleVisibility"
			:class="{
				'!pb-2': isVisible
			}"
		>
			<!-- <Button
				:icon="isVisible ? 'chevron-down' : 'chevron-right'"
				variant="ghost"
				@click="toggleVisibility"
			></Button> -->
			<div>
				<p class="font-medium text-gray-800">
					{{ label }}
				</p>
				<p class="mt-2 text-sm text-gray-700" v-if="subLabel">
					{{ subLabel }}
				</p>
			</div>
		</div>

		<div v-if="isVisible" class="text-sm leading-normal">
			<slot></slot>
		</div>
	</div>
</template>

<script>
export default {
	name: 'ToggleContent',
	props: {
		label: {
			type: String,
			required: true
		},
		subLabel: {
			type: String,
			default: ''
		}
	},
	data() {
		return {
			isVisible: false
		};
	},
	methods: {
		toggleVisibility() {
			this.isVisible = !this.isVisible;
		}
	}
};
</script>
