<template>
	<Dialog
		v-model="showDialog"
		:options="{ title: `Change branch for ${app.title}` }"
	>
		<template #body-content>
			<div class="flex flex-col items-center">
				<Button
					class="w-min"
					v-if="$resources.branches.loading"
					:loading="true"
					loadingText="Loading..."
				/>
				<FormControl
					v-else
					class="w-full"
					label="Select Branch"
					type="select"
					:options="$resources.branches.data"
					v-model="selectedBranch"
				/>
				<ErrorMessage
					class="mt-2 w-full"
					:message="$resources.changeBranch.error"
				/>
			</div>
		</template>
		<template #actions>
			<Button
				v-if="!$resources.branches.loading"
				class="w-full"
				variant="solid"
				label="Change Branch"
				:loading="$resources.changeBranch.loading"
				@click="changeBranch()"
			/>
		</template>
	</Dialog>
</template>

<script>
export default {
	name: 'ChangeAppBranchDialog',
	emits: ['branchChange'],
	props: ['bench', 'app'],
	data() {
		return {
			selectedBranch: this.app.branch,
			showDialog: true
		};
	},
	resources: {
		branches() {
			return {
				url: 'press.api.bench.branch_list',
				params: {
					name: this.bench,
					app: this.app.name
				},
				auto: true,
				initialData: [],
				transform(data) {
					return data.map(d => d.name);
				}
			};
		},
		changeBranch() {
			return {
				url: 'press.api.bench.change_branch',
				onSuccess() {
					this.$emit('branchChange');
					this.showDialog = false;
				},
				validate() {
					if (this.selectedBranch == this.app.branch) {
						return 'Please select a different branch';
					}
				}
			};
		}
	},
	methods: {
		changeBranch() {
			this.$resources.changeBranch.submit({
				name: this.bench,
				app: this.app.name,
				to_branch: this.selectedBranch
			});
		}
	}
};
</script>
