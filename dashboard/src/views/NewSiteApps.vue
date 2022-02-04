<template>
	<div class="space-y-6">
		<div v-if="!this.privateBench">
			<h2 class="text-lg font-semibold">Select Frappe version</h2>
			<p class="text-base text-gray-700">
				Select the Frappe version for your site
			</p>
			<div class="mt-4">
				<Input
					type="select"
					v-model="selectedVersion"
					:options="versionOptions"
				/>
			</div>
		</div>
		<div v-if="regionOptions.length > 0">
			<h2 class="text-lg font-semibold">Select Region</h2>
			<p class="text-base text-gray-700">
				Select the datacenter region where your site should be created
			</p>
			<div class="mt-4">
				<RichSelect
					:value="selectedRegion"
					@change="$emit('update:selectedRegion', $event)"
					:options="regionOptions"
				/>
			</div>
		</div>
		<div v-if="publicApps.length || privateApps.length">
			<h2 class="text-lg font-semibold">Select apps to install</h2>
			<p class="text-base text-gray-700">
				Choose apps to install on your site. You can select apps published on
				marketplace or your private apps.
			</p>
			<div class="mt-4 space-y-4">
				<div v-if="publicApps.length">
					<h3 class="sr-only">Marketplace Apps</h3>
					<div
						class="-mx-2 mt-4 grid max-h-56 grid-cols-2 gap-4 overflow-y-auto px-2 py-2"
					>
						<SelectableCard
							v-for="publicApp in publicApps"
							:key="publicApp.app"
							@click.native="toggleApp(publicApp)"
							:title="
								publicApp.marketplace
									? publicApp.marketplace.title
									: publicApp.app_title
							"
							:image="
								publicApp.marketplace ? publicApp.marketplace.image : null
							"
							:selected="selectedApps.includes(publicApp.app)"
							v-show="!publicApp.frappe"
							fullCircleImage
						>
							<template #secondary-content>
								<a
									v-if="publicApp.marketplace"
									class="inline-block text-sm leading-snug text-blue-600"
									:href="'/' + publicApp.marketplace.route"
									target="_blank"
									@click.stop
								>
									Details
								</a>
								<span class="text-sm leading-snug text-gray-700" v-else>
									{{ publicApp.repository_owner }}/{{ publicApp.repository }}
								</span>
							</template>
						</SelectableCard>
						<div class="h-1 py-4" v-if="publicApps.length > 4"></div>
					</div>
				</div>
				<div v-if="privateApps.length > 0">
					<h3 class="text-sm font-medium">Your Private Apps</h3>
					<div
						class="mt- -mx-2 grid max-h-56 grid-cols-2 gap-4 overflow-y-auto px-2 py-2"
					>
						<SelectableCard
							v-for="app in privateApps"
							:key="app.app"
							@click.native="toggleApp(app)"
							:selected="selectedApps.includes(app.app)"
							:title="app.app_title"
							fullCircleImage
						>
							<div slot="secondary-content" class="text-base text-gray-700">
								{{ app.repository_owner }}:{{ app.branch }}
							</div>
						</SelectableCard>
					</div>
				</div>
			</div>
		</div>
		<div v-if="selectedApps.includes('erpnext')">
			<Input
				type="checkbox"
				label="I am okay if my details are shared with local certified Partner"
				@change="(val) => $emit('update:shareDetailsConsent', val)"
				:value="shareDetailsConsent"
			/>
		</div>
	</div>
</template>
<script>
import SelectableCard from '@/components/SelectableCard.vue';
import RichSelect from '@/components/RichSelect.vue';

export default {
	components: {
		SelectableCard,
		RichSelect
	},
	name: 'Apps',
	props: [
		'options',
		'selectedApps',
		'selectedGroup',
		'privateBench',
		'selectedRegion',
		'shareDetailsConsent'
	],
	data: function () {
		return {
			selectedVersion: null
		};
	},
	computed: {
		publicApps() {
			return this.apps
				.filter((app) => app.public)
				.map((app) => {
					app.marketplace = this.options.marketplace_apps[app.app] || null;
					return app;
				});
		},
		privateApps() {
			return this.apps.filter((app) => !app.public);
		},
		apps() {
			let group = this.getSelectedGroup();
			return group ? group.apps : [];
		},
		groupOptions() {
			if (!this.options || !this.selectedVersion) return [];
			let selectedVersion = this.options.versions.find(
				(version) => version.name == this.selectedVersion
			);
			return selectedVersion.groups.map((group) => group.name);
		},
		versionOptions() {
			return this.options.versions.map((group) => group.name);
		},
		regionOptions() {
			let group = this.getSelectedGroup();
			return group
				? group.clusters.map((d) => ({
						label: d.title,
						value: d.name,
						image: d.image
				  }))
				: [];
		}
	},
	watch: {
		selectedVersion(value) {
			if (!this.privateBench) {
				let selectedVersion = this.options.versions.find(
					(v) => v.name == value
				);
				this.$emit('update:selectedGroup', selectedVersion.groups[0].name);
			}
		},
		selectedGroup() {
			this.$emit('update:selectedApps', ['frappe']);
			if (this.regionOptions.length > 0) {
				this.$emit('update:selectedRegion', this.regionOptions[0].value);
			}
		}
	},
	async mounted() {
		if (this.privateBench) {
			this.selectedVersion = this.options.versions.find((v) =>
				v.groups.some((g) => g.name == this.selectedGroup)
			).name;
			this.$emit('update:selectedApps', ['frappe']);
		} else {
			this.selectedVersion = this.options.versions[0].name;
		}
	},
	methods: {
		toggleApp(app) {
			if (app.frappe) return;
			if (!this.selectedApps.includes(app.app)) {
				this.$emit('update:selectedApps', this.selectedApps.concat(app.app));
			} else {
				this.$emit(
					'update:selectedApps',
					this.selectedApps.filter((a) => a !== app.app)
				);
			}
		},
		getSelectedGroup() {
			if (!this.options || !this.selectedVersion || !this.selectedGroup) {
				return null;
			}
			let selectedVersion = this.options.versions.find(
				(v) => v.name == this.selectedVersion
			);
			let group = selectedVersion.groups.find(
				(g) => g.name == this.selectedGroup
			);
			return group;
		}
	}
};
</script>
