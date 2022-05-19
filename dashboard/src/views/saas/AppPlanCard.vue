<template>
	<div
		v-if="plan && !plan.is_free"
		class="z-10 cursor-pointer rounded-2xl border border-gray-100 p-5 shadow hover:border-gray-300"
		:class="[
			popular ? 'relative bg-blue-100' : '',
			selected ? 'relative ring-2 ring-inset ring-blue-500' : ''
		]"
	>
		<div
			v-if="popular"
			class="absolute -top-3 left-1/4 rounded-md bg-blue-500 py-1 px-2 text-center text-xs"
		>
			<h5 class="font-medium uppercase text-white">Most Popular</h5>
		</div>

		<input
			v-if="selected"
			type="checkbox"
			class="absolute top-3 right-3 h-4 w-4 rounded border-gray-300 text-blue-500"
			checked
			disabled
		/>

		<h2 class="text-lg font-semibold">{{ plan.plan }}</h2>
		<br />
		<h4 class="text-xl font-semibold text-gray-900">
			<span>
				{{
					$planTitle({
						price_usd: plan.price_usd,
						price_inr: plan.price_inr
					})
				}}
				<span v-if="!plan.is_free" class="text-base font-normal text-gray-600">
					/mo</span
				>
			</span>
		</h4>
		<h4
			v-if="plan.discounted"
			class="mt-1 text-base text-gray-600 line-through"
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
