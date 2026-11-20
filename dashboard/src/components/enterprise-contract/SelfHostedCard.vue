<template>
	<div
		class="mx-auto flex max-w-2xl flex-wrap items-center gap-4 rounded-lg border bg-surface-gray-1 p-5 sm:px-8"
	>
		<div
			class="grid size-10 shrink-0 place-items-center rounded-lg border bg-surface-white"
		>
			<lucide-shield-check class="size-5 text-ink-gray-8" />
		</div>
		<div class="flex min-w-60 flex-1 flex-col gap-1">
			<h2 class="text-base font-medium text-ink-gray-9">
				Running Frappe on your own servers?
			</h2>
			<p class="text-base text-ink-gray-7">
				Get a yearly Enterprise Warranty from Frappe for the apps you run. No
				hosting on Frappe Cloud needed.
			</p>
		</div>
		<Button
			variant="solid"
			label="See Enterprise Warranty"
			:route="{ name: 'Enterprise Warranty' }"
		/>
	</div>
</template>

<script setup>
import { Button } from 'frappe-ui'
</script>
