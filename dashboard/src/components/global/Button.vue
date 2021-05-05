<template>
	<button
		:class="buttonClasses"
		@click="handleClick"
		v-bind="$attrs"
		v-on="$listeners"
		:disabled="isDisabled"
	>
		<svg
			v-if="loading"
			class="w-3 h-3 mr-2 -ml-1 animate-spin"
			:class="{
				'text-white': type == 'primary',
				'text-gray-600': type == 'secondary',
				'text-red-200': type == 'danger'
			}"
			xmlns="http://www.w3.org/2000/svg"
			fill="none"
			viewBox="0 0 24 24"
		>
			<circle
				class="opacity-25"
				cx="12"
				cy="12"
				r="10"
				stroke="currentColor"
				stroke-width="4"
			></circle>
			<path
				class="opacity-75"
				fill="currentColor"
				d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
			></path>
		</svg>
		<FeatherIcon v-else-if="iconLeft" :name="iconLeft" class="w-4 h-4 mr-1.5" />
		<template v-if="loading && loadingText">
			{{ loadingText }}
		</template>
		<template v-else-if="icon">
			<FeatherIcon :name="icon" class="w-4 h-4" />
		</template>
		<template v-else>
			<slot></slot>
		</template>
		<FeatherIcon v-if="iconRight" :name="iconRight" class="w-4 h-4 ml-2" />
	</button>
</template>
<script>
import FeatherIcon from './FeatherIcon.vue';

export default {
	name: 'Button',
	components: {
		FeatherIcon
	},
	props: {
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
		icon: {
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
		},
		route: {},
		link: {
			type: String,
			default: null
		}
	},
	computed: {
		buttonClasses() {
			return [
				'inline-flex items-center justify-center text-base leading-5 rounded-md focus:outline-none',
				this.icon ? 'p-1.5' : 'px-3 py-1',
				{
					'opacity-50 cursor-not-allowed pointer-events-none': this.isDisabled,
					'bg-gradient-blue hover:bg-gradient-none hover:bg-blue-500 text-white focus:shadow-outline-blue':
						this.type === 'primary',
					'bg-gray-100 hover:bg-gray-200 text-gray-900 focus:shadow-outline-gray':
						this.type === 'secondary',
					'bg-red-500 hover:bg-red-400 text-white focus:shadow-outline-red':
						this.type === 'danger',
					'bg-white text-gray-900 shadow focus:ring focus:ring-gray-400':
						this.type === 'white'
				}
			];
		},
		isDisabled() {
			return this.disabled || this.loading;
		}
	},
	methods: {
		handleClick() {
			this.route && this.$router.push(this.route);
			this.link ? window.open(this.link, '_blank') : null;
		}
	}
};
</script>
