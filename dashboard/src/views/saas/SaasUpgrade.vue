<template>
	<div class="mt-8 flex-1">
		<Alert
			class="flex-1"
			title="Please upgrade plan or else your services with frappeteams will be discontinued from."
		/>
		<div class="mt-4 flex">
			<div
				v-for="plan in plansData"
				v-bind:key="plan.plan"
				class="relative relative mx-2 mt-2 flex-1 cursor-pointer rounded-2xl border border-gray-100 p-5 shadow hover:border-gray-300"
			>
			<h3>{{ plan.plan }}</h3></br>
				<span v-if="plan.price_usd > 0" class="font-semibold text-2xl">
					{{
						$planTitle({
							price_usd: plan.price_usd,
							price_inr: plan.price_inr
						})
					}}
					<span class="text-base font-normal text-gray-600"> /mo</span>
				</span>

				<ul class="mt-5 space-y-2 text-sm text-gray-700">
					<li v-for="feature in plan.features" class="flex flex-row justify-items-center">
						<div
							class="mr-2 grid h-4 w-4 shrink-0 place-items-center rounded-full border border-green-500 bg-green-50"
						>
							<svg
								width="10"
								height="8"
								viewBox="0 0 10 8"
								fill="none"
								xmlns="http://www.w3.org/2000/svg"
							>
								<path
									d="M1.26562 3.86686L3.93229 6.53353L9.26562 1.2002"
									stroke="#38A160"
									stroke-miterlimit="10"
									stroke-linecap="round"
									stroke-linejoin="round"
								></path>
							</svg>
						</div>
						{{ feature }}
					</li>
				</ul>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'SaasUpgrade',
	data() {
		return {
			plansData: null
		};
	},
	resources: {
		plans: {
			method: 'press.api.saas.get_plans',
			auto: true,
			onSuccess(r) {
				this.plansData = r
			}
		}
	}
};
</script>
