<template>
	<Dialog
		v-if="source"
		:options="{
			title: 'Change Branch for ' + version + ' of ' + app,
			actions: [
				{
					label: 'Change Branch',
					variant: 'solid',
					loading: $resources.changeBranch.loading,
					onClick: () => changeBranch(),
				},
			],
		}"
		v-model="show"
	>
		<template v-slot:body-content>
			<div v-if="$resources.branches.loading" class="mt-2 flex justify-center">
				<LoadingText />
			</div>
			<ErrorMessage
				v-else-if="$resources.branches.error"
				:message="$resources.branches.error"
			/>
			<select
				v-else-if="$resources.branches.data"
				class="form-select block w-full"
				v-model="selectedBranch"
			>
				<option v-for="branch in branchList()" :key="branch">
					{{ branch }}
				</option>
			</select>
		</template>
	</Dialog>
</template>

<script>
import { toast } from 'vue-sonner';
import { getToastErrorMessage } from '../../utils/toast';
import { DashboardError } from '../../utils/error';

export default {
	name: 'ChangeAppBranchDialog',
	data() {
		return {
			show: true,
			selectedBranch: null,
		};
	},
	props: ['app', 'source', 'version', 'activeBranch'],
	emits: ['branch-changed'],
	resources: {
		branches() {
			return {
				url: 'press.api.marketplace.branches',
				params: {
					name: this.source,
				},
				auto: true,
			};
		},
		changeBranch() {
			return {
				url: 'press.api.marketplace.change_branch',
				params: {
					name: this.app,
					source: this.source,
					version: this.version,
					to_branch: this.selectedBranch,
				},
				validate() {
					if (this.selectedBranch == this.app.branch) {
						throw new DashboardError('Please select a different branch');
					}
				},
			};
		},
	},
	methods: {
		changeBranch() {
			toast.promise(this.$resources.changeBranch.submit(), {
				loading: 'Updating branch for version...',
				success: () => {
					this.show = false;
					this.$emit('branch-changed');
					return 'Branch changed successfully';
				},
				error: (e) => getToastErrorMessage(e),
			});
		},
		branchList() {
			if (this.$resources.branches.loading || !this.$resources.branches.data) {
				return [];
			}
			return this.$resources.branches.data.map((d) => d.name);
		},
	},
	mounted() {
		this.selectedBranch = this.activeBranch;
	},
};
</script>
