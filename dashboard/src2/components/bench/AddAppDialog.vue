<template>
	<Dialog
		:options="{ title: 'Add apps to your bench', position: 'top' }"
		v-model="showDialog"
	>
		<template v-slot:body-content>
			<FormControl
				class="mb-2"
				placeholder="Search for Apps"
				v-on:input="e => updateSearchTerm(e.target.value)"
			/>
			<LoadingText class="py-2" v-if="$resources.installableApps.loading" />
			<AppSourceSelector
				v-else
				class="max-h-96 overflow-auto p-1"
				:class="filteredOptions.length > 5 ? 'pr-2' : ''"
				:apps="filteredOptions"
				v-model="selectedApps"
				:multiple="true"
			/>
			<p class="mt-4 text-base" @click="showDialog = false">
				Don't find your app here?
				<Link :to="`/benches/${benchName}/apps/new`"> Add from GitHub </Link>
			</p>
		</template>
		<template v-slot:actions>
			<Button
				variant="solid"
				class="w-full"
				v-if="selectedApps.length > 0"
				:loading="$resources.addApps.loading"
				@click="
					$resources.addApps.submit({
						name: benchName,
						apps: selectedApps.map(app => ({
							app: app.app,
							source: app.source.name
						}))
					})
				"
			>
				Add App{{ selectedApps.length > 1 ? 's' : '' }}
			</Button>
		</template>
	</Dialog>
</template>

<script>
import AppSourceSelector from '@/components/AppSourceSelector.vue';
import Fuse from 'fuse.js/dist/fuse.basic.esm';

export default {
	name: 'AddAppDialog',
	props: ['benchName'],
	emits: ['appAdd'],
	data() {
		return {
			searchTerm: '',
			showDialog: true,
			selectedApps: [],
			filteredOptions: [],
			appToChangeBranchOf: null
		};
	},
	resources: {
		addApps: {
			url: 'press.api.bench.add_apps',
			onSuccess() {
				this.$emit('appAdd');
				this.showDialog = false;
			}
		},
		installableApps() {
			return {
				url: 'press.api.bench.installable_apps',
				params: {
					name: this.benchName
				},
				onSuccess(data) {
					this.fuse = new Fuse(data, {
						limit: 20,
						keys: ['title']
					});
					this.filteredOptions = data;
				},
				auto: true
			};
		}
	},
	methods: {
		updateSearchTerm(value) {
			if (value) {
				this.filteredOptions = this.fuse
					.search(value)
					.map(result => result.item);
			} else {
				this.filteredOptions = this.$resources.installableApps.data;
			}
		}
	}
};
</script>
