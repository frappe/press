<template>
	<Dialog
		:options="{
			title: `Edit ${dependency.title}`,
			actions: [
				{
					label: 'Update',
					variant: 'solid',
					loading: groupDocResource?.updateDependency?.loading,
					onClick: updateDependency
				}
			]
		}"
		v-model="showDialog"
	>
		<template #body-content>
			<div class="space-y-4">
				<!-- Custom dependency version -->
				<div v-if="useCustomVersion">
					<FormControl
						type="data"
						:label="`Custom ${dependency.title}`"
						placeholder="Please enter a custom version"
						description="Please ensure entered version of this dependency exists before setting it"
						v-model="customVersion"
					/>
				</div>

				<!-- Non custom version -->
				<FormControl
					v-else
					type="select"
					:disabled="useCustomVersion"
					:label="dependency.title"
					placeholder="Please select a version"
					:options="dependencyOptions"
					v-model="selectedDependencyVersion"
				/>

				<!-- Use Custom Version Checkbox -->
				<div class="flex items-center gap-2">
					<FormControl
						type="checkbox"
						label="Use Custom Version"
						v-model="useCustomVersion"
					/>
					<Tooltip text="View documentation">
						<a
							class="no-underline"
							target="_blank"
							href="https://optibizpro.com/docs/benches/editing-bench-dependency-version#setting-a-custom-version"
							><FeatherIcon
								name="help-circle"
								class="h-3 w-3 text-gray-700"
							></FeatherIcon
						></a>
					</Tooltip>
				</div>

				<ErrorMessage
					:message="groupDocResource?.updateDependency?.error || error"
				/>
			</div>
		</template>
	</Dialog>
</template>

<script>
import { getCachedDocumentResource } from 'frappe-ui';

export default {
	name: 'DependencyEditorDialog',
	props: {
		group: { required: true, type: Object },
		dependency: { required: true, type: Object }
	},
	data() {
		return {
			error: '',
			showDialog: true,
			customVersion: '',
			useCustomVersion: false,
			selectedDependencyVersion: null,
			groupDocResource: getCachedDocumentResource(
				'Release Group',
				this.group.name
			)
		};
	},
	mounted() {
		if (this.dependency.is_custom) {
			this.useCustomVersion = true;
			this.customVersion = this.dependency.version;
		} else {
			this.selectedDependencyVersion = this.dependency.version;
		}
	},
	computed: {
		dependencyOptions() {
			const versions = new Set(this.$resources.dependencyVersions.data ?? []);
			if (!this.dependency.is_custom) {
				versions.add(this.dependency.version);
			}

			return Array.from(versions)
				.sort()
				.map(v => ({
					label: v,
					value: v
				}));
		},
		version() {
			if (this.useCustomVersion) {
				return this.customVersion;
			}

			return this.selectedDependencyVersion;
		}
	},
	resources: {
		dependencyVersions() {
			return {
				type: 'list',
				doctype: 'Bench Dependency Version',
				fields: ['version'],
				filters: {
					parenttype: 'Bench Dependency',
					parent: this.dependency.dependency,
					supported_frappe_version: this.group.version
				},
				transform(data) {
					return data.map(d => d.version);
				},
				orderBy: 'version asc',
				pageLength: 1000,
				auto: true
			};
		}
	},
	methods: {
		setErrorIfCannotUpdate() {
			if (!this.version) {
				const verb = this.useCustomVersion ? 'enter' : 'select';
				this.error = `Please ${verb} a version`;
				return true;
			}

			if (this.dependency.version === this.version) {
				const verb = this.useCustomVersion ? 'Entered' : 'selected';
				this.error = `${verb} version is same as the previous version`;
				return true;
			}

			this.error = '';
			return false;
		},
		updateDependency() {
			if (this.setErrorIfCannotUpdate()) {
				return;
			}

			this.groupDocResource.updateDependency.submit(
				{
					dependency_name: this.dependency.name,
					version: this.version,
					is_custom: this.useCustomVersion
				},
				{
					onSuccess: () => {
						this.$emit('success');
						this.showDialog = false;
					}
				}
			);
		}
	}
};
</script>
