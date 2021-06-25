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
					<FeatherIcon v-if="deployFrom(app)" name="arrow-right" class="w-4" />
					<Badge color="green" v-else>First Deploy</Badge>
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
			if (app.will_branch_change) {
				return app.current_branch;
			}

			return app.current_hash
				? app.current_tag || app.current_hash.slice(0, 7)
				: null;
		},
		deployTo(app) {
			if (app.will_branch_change) {
				return app.branch;
			}
			
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
