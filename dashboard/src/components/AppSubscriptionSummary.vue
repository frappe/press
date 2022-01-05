<template>
	<div class="max-w-md">
		<h3>All apps (3)</h3>

		<ul class="mt-5 divide-y divide-gray-300">
			<li class="flex flex-row justify-between items-start pb-3">
				<div class="flex flex-row self-end">
					<!-- Replace with app icon -->
					<div class="h-10 w-10 bg-red-400 rounded-lg mr-3 self-center"></div>
					<div class="flex flex-col">
						<h4 class="text-gray-900 font-medium text-lg">Sentry</h4>
						<p class="text-gray-600 text-base mt-1">Best open source ERP.</p>
					</div>
				</div>
				<div class="flex flex-col">
					<div
						class="py-1 px-2 text-xs text-blue-500 bg-blue-100 rounded-md uppercase"
					>
						Most popular
					</div>
					<p
						class="text-xl text-gray-900 font-semibold mt-1 text-right self-end"
					>
						$10<span class="text-gray-600 text-base font-normal">/ Month</span>
					</p>
				</div>
			</li>
			<li class="flex flex-row justify-between items-center py-3">
				<div class="flex flex-row self-end">
					<!-- Replace with app icon -->
					<div class="h-10 w-10 bg-green-400 rounded-lg mr-3 self-center"></div>
					<div class="flex flex-col">
						<h4 class="text-gray-900 font-medium text-lg">Sentry</h4>
						<p class="text-gray-600 text-base mt-1">Best open source ERP.</p>
					</div>
				</div>
				<div class="flex flex-col">
					<p
						class="text-xl text-gray-900 font-semibold mt-1 text-right self-center"
					>
						$49<span class="text-gray-600 text-base font-normal">/ Month</span>
					</p>
				</div>
			</li>
			<li class="flex flex-row justify-between items-center py-3">
				<div class="flex flex-row self-end">
					<!-- Replace with app icon -->
					<div class="h-10 w-10 bg-indigo-400 rounded-lg mr-3 self-center"></div>
					<div class="flex flex-col">
						<h4 class="text-gray-900 font-medium text-lg">Sentry</h4>
						<p class="text-gray-600 text-base mt-1">Best open source ERP.</p>
					</div>
				</div>
				<div class="flex flex-col">
					<p
						class="text-xl text-gray-900 font-semibold mt-1 text-right self-end"
					>
						$129<span class="text-gray-600 text-base font-normal">/ Month</span>
					</p>
				</div>
			</li>
		</ul>
	</div>
</template>

<script>
export default {
	name: 'AppSubscriptionSummary',
	data() {
		return {};
	}
};
</script>
