<template>
	<div>
		<Section
			title="App information"
			description="General information about your app"
		>
			<SectionCard>
				<div class="grid grid-cols-3 px-6 py-3 text-base">
					<div class="font-medium text-gray-700">App name:</div>
					<div class="col-span-2 font-medium">{{ app.name }}</div>
				</div>
				<div class="grid grid-cols-3 px-6 py-3 text-base">
					<div class="font-medium text-gray-700">Created:</div>
					<div class="col-span-2 font-medium">
						<FormatDate>{{ app.created }}</FormatDate>
					</div>
				</div>
				<div class="grid grid-cols-3 px-6 py-3 text-base">
					<div class="font-medium text-gray-700">Last update:</div>
					<div class="col-span-2 font-medium">
						<FormatDate>{{ app.last_updated }}</FormatDate>
					</div>
				</div>
				<div class="grid grid-cols-3 px-6 py-3 text-base">
					<div class="font-medium text-gray-700">Branch:</div>
					<div class="col-span-2 font-medium">{{ app.branch }}</div>
				</div>
				<div class="grid grid-cols-3 px-6 py-3 text-base">
					<div class="font-medium text-gray-700">Repository:</div>
					<div class="col-span-2 font-medium">{{ app.repo }}</div>
				</div>
				<div class="grid grid-cols-3 px-6 py-3 text-base">
					<div class="font-medium text-gray-700">Owner:</div>
					<div class="col-span-2 font-medium">{{ app.owner }}</div>
				</div>
			</SectionCard>
		</Section>
		<Section
			class="mt-10"
			title="Installed apps"
			description="Apps installed on your app"
		>
			<SectionCard>
				<a
					class="block px-6 py-3 hover:bg-gray-50"
					v-for="app in app.installed_apps"
					:href="`${app.url}/tree/${app.branch}`"
					:key="app.url"
					target="_blank"
				>
					<p class="text-base font-medium text-brand">
						{{ app.owner }}/{{ app.repo }}
					</p>
					<p class="text-sm text-gray-800">
						{{ app.branch }}
					</p>
				</a>
			</SectionCard>
		</Section>
	</div>
</template>

<script>
export default {
	name: 'AppGeneral',
	props: ['app']
};
</script>
