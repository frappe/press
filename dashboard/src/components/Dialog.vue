<template>
	<Modal :show="show" @change="$emit('change', $event)">
		<div class="px-4 pt-5 pb-4 bg-white sm:p-6 sm:pb-4">
			<div class="sm:flex sm:items-start">
				<div class="w-full mt-3 sm:mt-0 sm:text-left">
					<div class="flex items-center justify-between">
						<h3 class="text-xl font-medium leading-6 text-gray-900">
							{{ title }}
						</h3>
						<button @click="$emit('change', false)">
							<FeatherIcon name="x" class="w-4 h-4" />
						</button>
					</div>
					<div class="mt-4 leading-5 text-gray-800">
						<slot></slot>
					</div>
				</div>
			</div>
		</div>
		<div
			class="flex items-center justify-end p-4 sm:px-6 sm:py-4"
			v-if="$slots.actions"
		>
			<slot name="actions"></slot>
		</div>
	</Modal>
</template>

<script>
import Modal from './Modal';
export default {
	name: 'Dialog',
	model: {
		prop: 'show',
		event: 'change'
	},
	props: ['title', 'show'],
	components: {
		Modal
	}
};
</script>
