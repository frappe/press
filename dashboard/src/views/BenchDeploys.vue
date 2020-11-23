<template>
	<div>
		<Section
			title="Deploys"
			:description="
				deploys.length ? 'Deploys on your bench' : 'No deploys on your bench'
			"
		>
			<div class="flex" v-if="deploys.length">
				<div
					class="w-full py-4 overflow-auto text-base border rounded-md sm:w-1/3 sm:rounded-r-none"
					:class="{ 'hidden sm:block': selectedDeploy }"
				>
					<router-link
						class="block px-6 py-3 cursor-pointer"
						:class="
							selectedDeploy && selectedDeploy.name === deploy.name
								? 'bg-gray-100'
								: 'hover:bg-gray-50'
						"
						v-for="deploy in deploys"
						:key="deploy.name"
						:to="`/benches/${bench.name}/deploys/${deploy.name}`"
					>
						Deploy on
						<FormatDate>
							{{ deploy.creation }}
						</FormatDate>
					</router-link>
				</div>
				<div class="w-full sm:w-2/3" v-if="selectedDeploy">
					{{ selectedDeploy }}
				</div>
			</div>
		</Section>
	</div>
</template>

<script>
export default {
	name: 'BenchDeploys',
	props: ['bench', 'deployName'],
	watch: {
		deployName(value) {
			if (value) {
				this.$resources.selectedDeploy.reload();
			}
		}
	},
	mounted() {
		if (this.deployName) {
			this.$resources.selectedDeploy.reload();
		}
	},
	resources: {
		deploys() {
			return {
				method: 'press.api.bench.deploys',
				params: {
					name: this.bench.name
				},
				auto: true,
				default: {
					deploys: [],
					update_available: false,
					candidate: null
				}
			};
		},
		selectedDeploy() {
			return {
				method: 'press.api.bench.deploy',
				params: {
					name: this.deployName
				},
				auto: false
			};
		}
	},
	computed: {
		selectedDeploy() {
			return this.$resources.selectedDeploy.data;
		},
		deploys() {
			return this.$resources.deploys.data;
		}
	}
};
</script>
