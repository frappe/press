<template>
	<div class="mt-4">
		<details class="cursor-pointer px-6" :key="sectionName" :open="defaultOpen">
			<summary class="inline-flex w-full items-center py-2 focus:outline-none">
				<span class="ml-1">
					<div
						class="grid h-4 w-4 place-items-center rounded-full border"
						:class="{
							'border-green-500 bg-green-50': sectionData,
							'border-gray-500 bg-gray-50': 'Skipped'
						}"
					>
						<FeatherIcon
							:name="
								// prettier-ignore
								sectionData
									? 'check'
									: 'minus'
							"
							:class="{
								'text-green-500': sectionData,
								'text-gray-500': 'Skipped'
							}"
							:stroke-width="3"
							class="h-3 w-3"
						/>
					</div>
				</span>
				<span class="ml-2 select-none text-sm font-medium text-gray-900">
					{{ sectionName }}
				</span>
			</summary>

			<div
				class="rounded-md bg-gray-100 px-2 py-2.5 font-mono text-xs text-gray-900 overflow-auto mt-3"
				:style="{
					width: viewportWidth < 768 ? 'calc(100vw - 6rem)' : ''
				}"
			>
				<div class="max-w-md">
					<pre>{{ sectionData }}</pre>
				</div>
			</div>
		</details>
	</div>
</template>
<script>
export default {
	name: 'InfoSection',
	props: ['sectionName', 'sectionData', 'defaultOpen']
};
</script>

<style scoped>
details > summary {
	list-style-type: none;
}

details > summary::-webkit-details-marker {
	display: none;
}

details > summary::before {
	content: url("data:image/svg+xml,%3Csvg width='12' height='12' viewBox='0 0 12 12' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M4.25 9.5L7.75 6L4.25 2.5' stroke='%231F272E' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
}

details[open] > summary::before {
	content: url("data:image/svg+xml,%3Csvg width='12' height='12' viewBox='0 0 12 12' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M2.5 4.25L6 7.75L9.5 4.25' stroke='%231F272E' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E%0A");
}
</style>
