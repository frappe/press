<template>
	<div class="pt-4">
		<PageHeader>
			<h1 slot="title">Apps</h1>
		</PageHeader>
		<div class="px-4 sm:px-8">
			<div
				class="p-24 text-center"
				v-if="$resources.apps.data && $resources.apps.data.length === 0"
			>
				<div class="text-xl text-gray-800">
					You haven't added any apps yet.
				</div>
				<Button class="mt-10" type="primary">
					<a href="/marketplace/submit-app" target="_blank">Submit your app</a>
				</Button>
			</div>
			<div v-else>
				<div
					class="grid items-center grid-cols-2 gap-12 py-4 text-sm text-gray-600 border-b md:grid-cols-4"
				>
					<span>App Name</span>
					<span class="text-right md:text-center">Status</span>
					<span class="hidden text-right md:inline">Added On</span>
					<span class="hidden md:inline"></span>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'Apps',
	resources: {
		apps: 'press.api.marketplace.apps',
	}
};
</script>
