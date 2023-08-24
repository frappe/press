<template>
	<div class="max-h-96 overflow-auto my-2">
		<div
			v-for="(site, index) in sites"
			:key="site.name"
			@click="$emit('update:selectedSite', site)"
			class="focus-within:shadow-outline flex cursor-pointer border px-4 py-3 text-left text-base"
			:class="[
				selectedSite === site ? 'bg-blue-50' : 'hover:bg-blue-50',
				{
					'border-b-0':
						sites.length > 1 && ![sites.length - 1, 0].includes(index),
					'rounded-b-md': sites.length > 1 && index === sites.length - 1,
					'rounded-t-md border-b-0': sites.length > 1 && index === 0,
					'rounded-md border': sites.length == 1
				}
			]"
		>
			<div class="flex flex-row items-center gap-2">
				<input type="radio" :checked="selectedSite === site" />
				<div class="text-lg font-medium text-gray-900 group-select">
					{{ site.name }}
				</div>
			</div>
		</div>
	</div>
</template>
<script>
export default {
	name: 'SiteRestoreSelector',
	props: ['sites', 'selectedSite'],
	emits: ['update:selectedSite']
};
</script>
