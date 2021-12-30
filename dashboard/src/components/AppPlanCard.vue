<template>
	<div
		v-if="plan"
		class="p-5 rounded-2xl shadow-lg cursor-pointer"
		:class="[
			popular ? 'bg-blue-100 relative' : '',
			selected ? 'ring-2 ring-blue-500 relative' : ''
		]"
	>
		<div
			v-if="popular"
			class="-top-3 left-1/4 absolute py-1 px-2 text-xs bg-blue-500 text-center rounded-md"
		>
			<h5 class="uppercase text-white font-medium">Most Popular</h5>
		</div>

		<input
			v-if="selected"
			type="checkbox"
			class="absolute
				top-3
				right-3
				h-4
				w-4
				text-blue-500
				border-gray-300
				rounded"
			checked
		/>

		<h4 class="text-gray-900 font-semibold text-xl">
			{{ plan.price
			}}<span class="font-normal text-gray-600 text-base">/ Month</span>
		</h4>
		<h4 class="mt-1 text-gray-600 text-base line-through">
			{{ plan.discountedFrom }}
		</h4>

		<FeatureList class="mt-5" :features="plan.features" />
	</div>
</template>

<script>
import FeatureList from '@/components/FeatureList.vue';

export default {
	name: 'AppPlanCard',
	props: {
		plan: {
			type: Object
		},
		popular: {
			type: Boolean,
			default: false
		},
		selected: {
			type: Boolean,
			default: false
		}
	},
	components: {
		FeatureList
	}
};
</script>
