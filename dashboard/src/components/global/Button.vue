<template>
	<button
		class="inline-flex items-center justify-center px-4 py-2 text-sm font-medium leading-5 border rounded-md focus:outline-none "
		:class="{
			'opacity-50 cursor-not-allowed pointer-events-none': isDisabled,
			'bg-blue-500 border-transparent hover:bg-blue-400 text-white focus:shadow-outline-blue focus:border-blue-700':
				type === 'primary',
			'bg-white border-gray-400 hover:text-gray-800 text-gray-900 focus:shadow-outline-blue focus:border-blue-300':
				type === 'secondary',
			'bg-red-500 border-transparent hover:bg-red-400 text-white focus:shadow-outline-red focus:border-red-700':
				type === 'danger'
		}"
		@click="route && $router.push(route)"
		v-bind="$attrs"
		v-on="$listeners"
		:disabled="isDisabled"
	>
		<FeatherIcon v-if="iconLeft" :name="iconLeft" class="w-4 h-4 mr-2" />
		<template v-if="loading && loadingText">
			{{ loadingText }}
		</template>
		<template v-else>
			<slot></slot>
		</template>
		<FeatherIcon v-if="iconRight" :name="iconRight" class="w-4 h-4 ml-2" />
	</button>
</template>
<script>
import FeatherIcon from './FeatherIcon';

export default {
	name: 'Button',
	components: {
		FeatherIcon
	},
	props: {
		route: {},
		type: {
			type: String,
			default: 'secondary'
		},
		disabled: {
			type: Boolean,
			default: false
		},
		iconLeft: {
			type: String,
			default: null
		},
		iconRight: {
			type: String,
			default: null
		},
		loading: {
			type: Boolean,
			default: false
		},
		loadingText: {
			type: String,
			default: null
		}
	},
	computed: {
		isDisabled() {
			return this.disabled || this.loading;
		}
	}
};
</script>
