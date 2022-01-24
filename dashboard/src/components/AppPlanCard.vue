<template>
	<div
		v-if="plan"
		class="p-5 rounded-2xl shadow cursor-pointer border border-gray-100 hover:border-gray-300"
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
			disabled
		/>

		<h4 class="text-gray-900 font-semibold text-xl">
			<span v-if="plan.is_free">
				Free
			</span>

			<span v-else>
				{{ $planTitle(plan)
				}}<span class="font-normal text-gray-600 text-base"> /mo</span>
			</span>
		</h4>
		<h4
			v-if="plan.discounted"
			class="mt-1 text-gray-600 text-base line-through"
		>
			{{
				$planTitle({
					price_usd: plan.price_usd_before_discount,
					price_inr: plan.price_inr_before_discount
				})
			}}
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
