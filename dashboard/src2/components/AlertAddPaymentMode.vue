<template>
	<div
		class="flex items-center justify-between rounded-md border border-amber-200 bg-amber-100 px-3.5 py-2.5"
	>
		<i-lucide-alert-triangle class="h-4 w-4 text-amber-600" />
		<div class="ml-3 text-p-base font-medium text-gray-800">
			Add a payment mode to start creating sites, benches, and more.
		</div>
		<Button class="ml-auto" route="/welcome" variant="outline">
			Add payment mode
		</Button>
	</div>
</template>
<script>
export default {
	name: 'AlertAddPaymentMode'
};
</script>
