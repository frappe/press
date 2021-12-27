<template>
	<div class="grid grid-cols-5">
		<div class="p-5 rounded-2xl shadow-lg">
			<h4 class="text-gray-900 font-semibold text-xl">
				₹99<span class="font-normal text-gray-600 text-base">/ Month</span>
			</h4>
			<h4 class="mt-1 text-gray-600 text-base line-through">₹299</h4>

			<ul class="mt-5 text-base text-gray-700 space-y-2">
				<li class="flex flex-row items-center">
					<CircularCheckIcon class="mr-2" />
					1 member
				</li>
				<li class="flex flex-row items-center">
					<CircularCheckIcon class="mr-2" />
					7 day data rentention
				</li>
				<li class="flex flex-row items-center">
					<CircularCheckIcon class="mr-2" />
					1 GB
				</li>
			</ul>
		</div>
	</div>
</template>

<script>
export default {
	name: 'ChangeAppPlanCards',
	data() {
		return {};
	}
};
</script>
