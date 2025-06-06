<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-col rounded-lg text-base text-gray-900 shadow">
			<div class="flex flex-col gap-2.5 px-4 py-3">
				<div class="flex items-center justify-between">
					<div class="flex flex-col gap-1.5">
						<div class="text-lg font-semibold">Follow up Details</div>
						<div class="text-gray-700">
							<span>Next charge date — </span>
							<!-- <span>{{ currentMonthEnd() }}</span> -->
						</div>
					</div>
				</div>
				<div class="flex items-center justify-between">
					<div class="flex gap-2 text-gray-700">
						<i-lucide-credit-card class="h-4 w-4" />
						<div>
							<span>Current billing amount so far is </span>
							<span class="font-medium text-gray-900">
								<!-- {{ currency }} {{ currentBillingAmount?.toFixed(2) || '0.00' }} -->
							</span>
						</div>
					</div>
					<div>
						<Button label="View Invoice" @click="true" />
					</div>
				</div>
			</div>
			<div
				class="m-1.5 flex items-center justify-between rounded-lg bg-gray-50 px-2.5 py-2"
			>
				<div class="flex h-7 items-center gap-2 text-gray-800">
					<i-lucide-receipt class="h-4 w-4" />
					<div>
						<span>Unpaid amount is </span>
						<!-- <span>{{ currency }} {{ unpaidAmount.data?.toFixed(2) }}</span> -->
					</div>
				</div>
				<div>
					<Button variant="solid" label="Pay now" />
				</div>
			</div>
		</div>
	</div>
</template>
<script></script>
