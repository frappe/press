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
			</div>
			<div v-else>
				<div
					class="grid items-center grid-cols-2 gap-12 py-4 text-sm text-gray-700 border-b"
				>
					<span>App Name</span>
					<span class="text-right">Last Updated</span>
				</div>
				<a
					class="grid items-center grid-cols-2 gap-12 py-4 text-sm border-b hover:bg-gray-50 focus:outline-none focus:shadow-outline"
					v-for="app in $resources.apps.data"
					:key="app.name"
					:href="'#/apps/' + app.name"
				>
					<span>{{ app.title }}</span>
					<FormatDate class="text-right" type="relative">
						{{ app.modified }}
					</FormatDate>
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
	},
	mounted() {
		this.setupSocketListener();
	},
	methods: {
		setupSocketListener() {
			if (this._socketSetup) return;
			this._socketSetup = true;
			this.$socket.on('list_update', ({ doctype }) => {
				if (doctype === 'App' || doctype === 'App Release') {
					this.$resources.apps.reload();
				}
			});
		}
	}
};
</script>
