<template>
	<div
		class="mx-auto mb-6 mt-[12vh] flex max-w-xl flex-col items-center rounded-lg border border-dashed border-outline-gray-2 px-6 py-10 text-center"
	>
		<div
			class="flex size-10 items-center justify-center rounded-full bg-surface-gray-2"
		>
			<lucide-layout-grid class="size-5 text-ink-gray-6" />
		</div>
		<h3 class="mt-4 text-lg font-semibold text-ink-gray-9">
			Publish your app on the Marketplace
		</h3>
		<p class="mt-2 text-base leading-relaxed text-ink-gray-6">
			Built a Frappe app? List it on the Frappe Cloud Marketplace so other
			users can find and install it. You can offer it for free or as a paid
			app.
		</p>
		<Button
			class="mt-5"
			variant="solid"
			label="Learn how publishing works"
			link="https://docs.frappe.io/cloud/marketplace/publishing-an-app-to-marketplace"
		>
			<template #suffix><lucide-external-link class="size-3.5" /></template>
		</Button>
	</div>
</template>

<script setup>
import { Button } from 'frappe-ui';
</script>
