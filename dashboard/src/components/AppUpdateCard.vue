<template>
	<button
		class="flex w-full flex-row items-center justify-between rounded-lg border border-gray-100 px-4 py-2 shadow focus:outline-none"
		:class="[
			selected || uninstall ? 'ring-2 ring-inset ring-blue-500' : '',
			selectable ? 'hover:border-gray-300' : 'cursor-default'
		]"
	>
		<h3 class="text-lg font-medium text-gray-900">
			{{ app.title }}
		</h3>
		<Badge v-if="uninstall" color="red"> Will Be Uninstalled </Badge>
		<div v-else class="flex flex-row space-x-2">
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
	</button>
</template>

<script>
export default {
	name: 'AppUpdateCard',
	props: ['app', 'selectable', 'selected', 'uninstall'],
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
	}
};
</script>
