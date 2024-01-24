<template>
	<Dialog
		v-if="app"
		v-model="show"
		:options="{ title: `Change branch for ${app.title}` }"
	>
		<template v-slot:body-content>
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
					:options="branchList()"
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
	emits: ['update:app'],
	props: ['bench', 'app'],
	data() {
		return {
			selectedBranch: null
		};
	},
	resources: {
		branches() {
			return {
				url: 'press.api.bench.branch_list'
			};
		},
		changeBranch() {
			return {
				url: 'press.api.bench.change_branch',
				onSuccess() {
					window.location.reload();
				},
				validate() {
					if (this.selectedBranch == this.app.branch) {
						return 'Please select a different branch';
					}
				}
			};
		}
	},
	watch: {
		app(value) {
			if (value) {
				this.selectedBranch = value.branch;
				this.$resources.branches.submit({
					name: this.bench,
					app: value.name
				});
			}
		}
	},
	methods: {
		branchList() {
			if (this.$resources.branches.loading || !this.$resources.branches.data) {
				return [];
			}

			return this.$resources.branches.data.map(d => d.name);
		},
		changeBranch() {
			this.$resources.changeBranch.submit({
				name: this.bench,
				app: this.app.name,
				to_branch: this.selectedBranch
			});
		},
		dialogClosed() {
			this.$emit('update:app', null);
			this.$resources.changeBranch.reset();
		}
	},
	computed: {
		show: {
			get() {
				return Boolean(this.app && this.bench);
			},
			set(value) {
				if (!value) {
					this.dialogClosed();
				}
			}
		}
	}
};
</script>
