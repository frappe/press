<template>
	<div>
		<h3>All apps (3)</h3>

		<ul class="mt-5 divide-y divide-gray-300">
			<li class="flex flex-row items-start justify-between pb-3">
				<div class="flex flex-row self-end">
					<!-- Replace with app icon -->
					<div class="mr-3 h-10 w-10 self-center rounded-lg bg-red-400"></div>
					<div class="flex flex-col">
						<h4 class="text-lg font-medium text-gray-900">Frappe Mail</h4>
						<p class="mt-1 text-base text-gray-600">Best open source ERP.</p>
					</div>
				</div>
				<div class="flex flex-col">
					<div
						class="rounded-md bg-blue-100 py-1 px-2 text-xs uppercase text-blue-500"
					>
						Most popular
					</div>
					<p
						class="mt-1 self-end text-right text-xl font-semibold text-gray-900"
					>
						$10<span class="text-base font-normal text-gray-600">/ Month</span>
					</p>
				</div>
			</li>
			<li class="flex flex-row items-center justify-between py-3">
				<div class="flex flex-row self-end">
					<!-- Replace with app icon -->
					<div class="mr-3 h-10 w-10 self-center rounded-lg bg-green-400"></div>
					<div class="flex flex-col">
						<h4 class="text-lg font-medium text-gray-900">Darkify</h4>
						<p class="mt-1 text-base text-gray-600">Best open source ERP.</p>
					</div>
				</div>
				<div class="flex flex-col">
					<p
						class="mt-1 self-center text-right text-xl font-semibold text-gray-900"
					>
						$49<span class="text-base font-normal text-gray-600">/ Month</span>
					</p>
				</div>
			</li>
			<li class="flex flex-row items-center justify-between py-3">
				<div class="flex flex-row self-end">
					<!-- Replace with app icon -->
					<div
						class="mr-3 h-10 w-10 self-center rounded-lg bg-indigo-400"
					></div>
					<div class="flex flex-col">
						<h4 class="text-lg font-medium text-gray-900">Frappe Healthcare</h4>
						<p class="mt-1 text-base text-gray-600">Best open source ERP.</p>
					</div>
				</div>
				<div class="flex flex-col">
					<p
						class="mt-1 self-end text-right text-xl font-semibold text-gray-900"
					>
						$129<span class="text-base font-normal text-gray-600">/ Month</span>
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
