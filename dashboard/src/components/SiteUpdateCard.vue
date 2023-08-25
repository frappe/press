<template>
	<button
		class="flex w-full flex-row items-center justify-between rounded-lg border border-gray-100 px-4 py-2 shadow focus:outline-none"
		:class="[
			selected ? 'ring-2 ring-inset ring-blue-500' : '',
			selectable ? 'hover:border-gray-300' : 'cursor-default'
		]"
		ref="card"
	>
		<div class="flex flex-col">
			<div
				@click.self="$refs['card'].click()"
				class="flex flex-row items-center gap-2"
			>
				<input
					@click.self="$refs['card'].click()"
					v-if="selectable"
					:checked="selected"
					type="checkbox"
					class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-transparent"
				/>
				<h3 class="text-lg font-medium text-gray-900 group-select">
					{{ site }}
				</h3>
			</div>
			<div v-if="selected" class="flex flex-row mt-2">
				<Input
					@change="toggleProperty($event, 'skip_failing_patches', site)"
					type="checkbox"
					label="Skip failing patches"
					class="h-4 rounded border-gray-300 text-gray-600 focus:ring-transparent"
				/>
				<Input
					v-if="$account.team?.skip_backups"
					@change="toggleProperty($event, 'skip_backups', site)"
					type="checkbox"
					label="Skip backup"
					class="h-4 ml-2 rounded border-gray-300 text-gray-600 focus:ring-transparent"
				/>
			</div>
		</div>
	</button>
</template>

<script>
export default {
	name: 'SiteUpdateCard',
	props: ['site', 'selectable', 'selected', 'selectedSites'],
	methods: {
		toggleProperty(value, prop, site) {
			this.selectedSites.map(selectedSite => {
				if (site == selectedSite.name) {
					selectedSite[prop] = value;
				}
			});
			this.$emit('update:selectedSites', this.selectedSites);
		}
	}
};
</script>
