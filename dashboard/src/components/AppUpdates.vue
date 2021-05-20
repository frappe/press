<template>
	<div class="divide-y">
		<ListItem
			v-for="app in appsWithUpdates"
			:title="app.title"
			:subtitle="`${app.repository_owner}/${app.repository}:${app.branch}`"
			:key="app.app"
		>
			<template #actions>
				<div class="flex items-center space-x-1">
					<a
						v-if="deployFrom(app)"
						class="block cursor-pointer"
						:href="`${app.repository_url}/commit/${app.current_hash}`"
						target="_blank"
					>
						<Badge class="cursor-pointer hover:text-blue-500" color="blue">
							{{ deployFrom(app) }}
						</Badge>
					</a>
					<FeatherIcon name="arrow-right" class="w-4" />
					<a
						class="block cursor-pointer"
						:href="`${app.repository_url}/commit/${app.next_hash}`"
						target="_blank"
					>
						<Badge class="cursor-pointer hover:text-blue-500" color="blue">
							{{ deployTo(app) }}
						</Badge>
					</a>
				</div>
			</template>
		</ListItem>
	</div>
</template>
<script>
export default {
	name: 'AppUpdates',
	props: ['apps'],
	methods: {
		deployFrom(app) {
			return app.current_hash
				? app.current_tag || app.current_hash.slice(0, 7)
				: null;
		},
		deployTo(app) {
			return app.next_tag || app.next_hash.slice(0, 7);
		}
	},
	computed: {
		appsWithUpdates() {
			return this.apps.filter(app => app.update_available);
		}
	}
};
</script>
