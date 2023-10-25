<template>
	<Dialog :options="{ title: 'New Site' }" v-model="show">
		<template #body-content v-if="options">
			<div class="space-y-4">
				<div>
					<div class="flex w-full">
						<TextInput
							class="flex-1 rounded-r-none"
							placeholder="Subdomain"
							v-model="selectedValues.subdomain"
						/>
						<div class="flex items-center rounded-r bg-gray-100 px-4 text-base">
							.{{ options.domain }}
						</div>
					</div>
					<div class="mt-1">
						<ErrorMessage
							v-if="subdomainInvalidMessage"
							:message="subdomainInvalidMessage"
						/>
						<template
							v-if="
								!subdomainInvalidMessage && options.subdomain_available != null
							"
						>
							<div
								v-if="options.subdomain_available"
								class="text-sm text-green-600"
							>
								{{ selectedValues.subdomain }}.{{ options.domain }} is available
							</div>
							<div v-else class="text-sm text-red-600">
								{{ selectedValues.subdomain }}.{{ options.domain }} is not
								available
							</div>
						</template>
					</div>
				</div>
				<FormControl
					v-if="options.versions.length"
					label="Select Framework Version"
					type="select"
					:options="options.versions"
					v-model="selectedValues.version"
				/>
				<FormControl
					v-if="options.apps.length"
					label="Select App"
					type="select"
					:options="options.apps"
					v-model="selectedValues.app"
				/>
				<FormControl
					v-if="options.clusters.length"
					label="Select Cluster"
					type="select"
					:options="options.clusters"
					v-model="selectedValues.cluster"
				/>
				<!-- <Autocomplete :options="regionOptions" /> -->
			</div>
		</template>
	</Dialog>
</template>
<script>
import { Autocomplete, FormControl, TextInput, debounce } from 'frappe-ui';
import { validateSubdomain } from '../../src/utils.js';

export default {
	name: 'NewSiteDialog',
	data() {
		return {
			show: true,
			selectedValues: {
				subdomain: '',
				version: ''
			}
		};
	},
	watch: {
		selectedValues: {
			handler: debounce(function (val, oldVal) {
				if (!this.subdomainInvalidMessage) {
					console.log('reloading options');
					this.$resources.options.reload();
				}
			}, 500),
			deep: true
		}
	},
	components: { FormControl, TextInput, Autocomplete },
	resources: {
		options() {
			return {
				url: 'press.api.client.run_doctype_method',
				params: {
					doctype: 'Site',
					method: 'options_for_new',
					selected_values: this.selectedValues
				},
				auto: true
			};
		}
	},
	computed: {
		options() {
			return this.$resources.options.data;
		},
		subdomainInvalidMessage() {
			if (this.selectedValues.subdomain) {
				return validateSubdomain(this.selectedValues.subdomain);
			}
		}
	}
};
</script>
