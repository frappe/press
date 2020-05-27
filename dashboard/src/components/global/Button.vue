<template>
	<button
		class="inline-flex items-center justify-center px-3 py-1 text-base leading-5 rounded-md focus:outline-none"
		:class="{
			'opacity-50 cursor-not-allowed pointer-events-none': isDisabled,
			'bg-gradient-blue hover:bg-gradient-none hover:bg-blue-500 text-white focus:shadow-outline-blue':
				type === 'primary',
			'bg-gray-50 hover:bg-gray-100 text-gray-900 focus:shadow-outline-gray':
				type === 'secondary',
			'bg-red-500 hover:bg-red-400 text-white focus:shadow-outline-red':
				type === 'danger'
		}"
		@click="route && $router.push(route)"
		v-bind="$attrs"
		v-on="$listeners"
		:disabled="isDisabled"
	>
		<FeatherIcon v-if="iconLeft" :name="iconLeft" class="w-4 h-4 mr-1.5" />
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
