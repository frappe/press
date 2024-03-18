<template>
	<Dialog
		:options="{
			title: 'Edit Dependency',
			actions: [
				{
					label: 'Edit',
					variant: 'solid',
					loading: groupDocResource?.updateDependency?.loading,
					onClick: editDependency
				}
			]
		}"
		v-model="showDialog"
	>
		<template #body-content>
			<div class="space-y-4">
				<FormControl
					type="select"
					:label="dependency.title"
					:options="dependencyOptions"
					v-model="selectedDependencyVersion"
				/>
				<ErrorMessage :message="groupDocResource?.updateDependency?.error" />
			</div>
		</template>
	</Dialog>
</template>

<script>
import { getCachedDocumentResource } from 'frappe-ui';

export default {
	name: 'DependencyEditorDialog',
	props: ['group', 'dependency'],
	data() {
		return {
			showDialog: true,
			selectedDependencyVersion: null,
			groupDocResource: getCachedDocumentResource(
				'Release Group',
				this.group.name
			)
		};
	},
	computed: {
		dependencyOptions() {
			const versions = [
				...new Set([
					...(this.$resources.dependencyVersions.data || []),
					this.dependency.version
				])
			].sort();
			this.selectedDependencyVersion = this.dependency.version;
			return versions.map(v => ({
				label: v,
				value: v
			}));
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
		editDependency() {
			this.groupDocResource.updateDependency.submit(
				{
					dependency_name: this.dependency.name,
					version: this.selectedDependencyVersion
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
