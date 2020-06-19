<template>
	<div class="pt-4">
		<PageHeader>
			<h1 slot="title">Apps</h1>
			<div class="flex items-center" slot="actions">
				<Button route="/apps/new" type="primary" iconLeft="plus"
					>New App</Button
				>
			</div>
		</PageHeader>
		<div class="px-4 sm:px-8">
			<div
				class="p-24 text-center"
				v-if="$resources.apps.data && $resources.apps.data.length === 0"
			>
				<div class="text-xl text-gray-800">
					You haven't added any apps yet.
				</div>
				<Button route="/apps/new" class="mt-10" type="primary"
					>Add your first App</Button
				>
			</div>
			<div v-else>
				<div
					class="grid items-center grid-cols-4 gap-12 py-4 text-sm text-gray-700 border-b"
				>
					<span>App Name</span>
					<span class="text-center">
						Status
					</span>
					<span class="text-right">Last Updated</span>
					<span></span>
				</div>
				<a
					class="grid items-center grid-cols-4 gap-12 py-4 text-sm border-b hover:bg-gray-50 focus:outline-none focus:shadow-outline"
					v-for="app in $resources.apps.data"
					:key="app.name"
					:href="'#/apps/' + app.name"
				>
					<span>{{ app.name }}</span>
					<span class="text-center">
						<Badge :status="app.status" />
					</span>
					<FormatDate class="text-right" type="relative">
						{{ app.modified }}
					</FormatDate>
					<span class="text-right">
						<Badge
							:status="'Update Available'"
							v-if="app.update_available"
							class="mr-4"
						/>
						<a
							:href="app.url"
							target="_blank"
							class="inline-flex items-baseline text-sm text-blue-500 hover:underline"
						>
							Visit Repo
							<FeatherIcon name="external-link" class="w-3 h-3 ml-1" />
						</a>
					</span>
				</a>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'Apps',
	resources: {
		apps: 'press.api.app.all'
	}
};
</script>
