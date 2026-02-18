<template>
	<Dialog
		v-model="showDialog"
		:options="{ title: `Change branch for ${app.title}` }"
	>
		<template #body-content>
			<div class="flex flex-col items-center gap-2 w-full">
				<LoadingText class="my-4" v-if="$resources.branches.loading" />

				<template v-else>
					<!-- Branch Selector -->
					<FormControl
						v-if="!useOtherBranch"
						class="w-full"
						label="Select Branch"
						type="select"
						:options="$resources.branches.data"
						v-model="selectedBranch"
					/>

					<!-- Other Branch Input -->
					<FormControl
						v-else
						class="w-full"
						label="Branch Name"
						type="text"
						placeholder="Enter branch name"
						v-model="otherBranchName"
					/>

					<!-- Other branches toggle -->
					<FormControl
						type="checkbox"
						label="Other branches"
						v-model="useOtherBranch"
						class="self-start"
					/>

					<!-- GitHub verification error -->
					<span
						v-if="branchVerificationError"
						class="text-sm text-red-600 w-full mt-3"
					>
						{{ branchVerificationError }}
					</span>

					<!-- GitHub verification error -->
					<span
						v-else-if="branchVerificationSuccess"
						class="text-sm text-green-600 w-full mt-3"
					>
						{{ branchVerificationSuccess }}
					</span>

					<ErrorMessage
						v-if="$resources.changeBranch?.error"
						class="mt-2 w-full"
						:message="$resources.changeBranch.error"
					/>
				</template>
			</div>
		</template>

		<template #actions>
			<!-- Validate button -->
			<Button
				v-if="useOtherBranch && !otherBranchValidated"
				class="w-full"
				variant="solid"
				label="Validate"
				:loading="validatingBranch"
				@click="validateOtherBranch"
			/>

			<!-- Change Branch button -->
			<Button
				v-else-if="canChangeBranch"
				class="w-full"
				variant="solid"
				label="Change Branch"
				:loading="$resources.changeBranch.loading"
				@click="changeBranch"
			/>
		</template>
	</Dialog>
</template>

<script>
import { DashboardError } from '../../utils/error';

export default {
	name: 'ChangeAppBranchDialog',
	emits: ['branchChange'],
	props: ['bench', 'app'],

	data() {
		return {
			selectedBranch: this.app.branch,
			otherBranchName: '',
			useOtherBranch: false,
			otherBranchValidated: false,
			branchVerificationError: null,
			branchVerificationSuccess: null,
			validatingBranch: false,
			showDialog: true,
		};
	},

	computed: {
		canChangeBranch() {
			if (this.useOtherBranch) {
				return this.otherBranchValidated;
			}
			return this.selectedBranch && this.selectedBranch !== this.app.branch;
		},
	},

	watch: {
		useOtherBranch() {
			this.otherBranchValidated = false;
			this.branchVerificationError = null;
		},
		otherBranchName() {
			this.otherBranchValidated = false;
			this.branchVerificationError = null;
			this.branchVerificationSuccess = null;
		},
	},

	resources: {
		branches() {
			return {
				url: 'press.api.bench.branch_list',
				params: {
					name: this.bench,
					app: this.app.name,
				},
				auto: true,
				initialData: [],
				transform(data) {
					return data.map((d) => d.name);
				},
			};
		},

		validateBranchUsingInstallation() {
			return {
				url: 'press.api.bench.validate_branch',
			};
		},

		changeBranch() {
			return {
				url: 'press.api.bench.change_branch',
				validate() {
					const targetBranch = this.useOtherBranch
						? this.otherBranchName
						: this.selectedBranch;

					if (!targetBranch || targetBranch === this.app.branch) {
						throw new DashboardError('Please select a different branch');
					}
				},
				onSuccess() {
					this.$emit('branchChange');
					this.showDialog = false;
				},
			};
		},
	},

	methods: {
		async validateOtherBranch() {
			this.$resources.changeBranch.reset();
			this.validatingBranch = true;
			this.branchVerificationError = null;
			try {
				await this.$resources.validateBranchUsingInstallation.submit({
					name: this.bench,
					app: this.app.name,
					branch: this.otherBranchName.trim(),
				});

				this.otherBranchValidated = true;
				this.branchVerificationSuccess = 'Branch validated successfully';
			} catch (e) {
				this.branchVerificationError = "Branch couldn't be verified on GitHub";
				this.otherBranchValidated = false;
			} finally {
				this.validatingBranch = false;
			}
		},

		changeBranch() {
			this.$resources.changeBranch.submit({
				name: this.bench,
				app: this.app.name,
				to_branch: this.useOtherBranch
					? this.otherBranchName.trim()
					: this.selectedBranch,
			});
		},
	},
};
</script>
