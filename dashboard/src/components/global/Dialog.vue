<template>
	<Modal
		:show="show"
		@update:show="handleChange"
		:dismissable="dismissable"
		:width="width"
	>
		<div class="bg-white px-4 pb-4 sm:px-6 sm:pb-4">
			<div class="sm:flex sm:items-start">
				<div class="relative w-full sm:text-left">
					<div class="sticky top-0 bg-white py-4">
						<h3 class="text-xl font-medium leading-6 text-gray-900">
							{{ title }}
						</h3>
						<p v-if="subtitle" class="mt-1.5 text-base text-gray-600">
							{{ subtitle }}
						</p>
					</div>
					<button
						v-if="dismissable"
						class="absolute top-0 right-0"
						@click="handleChange(false)"
					>
						<FeatherIcon name="x" class="mt-4 h-4 w-4" />
					</button>
					<div class="leading-5 text-gray-800">
						<slot></slot>
					</div>
				</div>
			</div>
		</div>
		<div
			class="sticky bottom-0 flex items-center justify-end bg-white p-4 sm:px-6 sm:py-4"
			v-if="$slots.actions"
		>
			<slot name="actions"></slot>
		</div>
	</Modal>
</template>

<script>
import Modal from '@/components/Modal.vue';
export default {
	name: 'Dialog',
	emits: ['update:modelValue', 'close'],
	props: ['title', 'subtitle', 'show', 'dismissable', 'width', 'modelValue'],
	components: {
		Modal
	},
	methods: {
		handleChange(value) {
			this.$emit('update:modelValue', value);
			if (value === false) {
				this.$emit('close');
			}
		}
	}
};
</script>
