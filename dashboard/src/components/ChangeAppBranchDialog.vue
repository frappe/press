<template>
	<Dialog
		v-if="app"
		:show="bench && app"
		:title="`Change branch for ${app.title}`"
		v-on:close="dialogClosed"
	>
		<div>
			<Button
				v-if="$resources.branches.loading"
				:loading="true"
				loadingText="Loading..."
			></Button>

			<div v-else>
				<select class="form-select block w-full" v-model="selectedBranch">
					<option v-for="branch in branchList()" :key="branch">
						{{ branch }}
					</option>
				</select>
				<Button
					class="mt-3"
					type="primary"
					:loading="this.$resources.changeBranch.loading"
					@click="changeBranch()"
				>
					Change Branch
				</Button>
			</div>

			<ErrorMessage class="mt-2" :error="$resourceErrors" />
		</div>
	</Dialog>
</template>

<script>
export default {
	name: 'ChangeAppBranchDialog',
	props: ['bench', 'app'],
	data() {
		return {
			selectedBranch: null
		};
	},
	resources: {
		branches() {
			return {
				method: 'press.api.bench.branch_list'
			};
		},
		changeBranch() {
			return {
				method: 'press.api.bench.change_branch',
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
	}
};
</script>
