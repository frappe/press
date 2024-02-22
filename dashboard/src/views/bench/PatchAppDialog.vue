<template>
	<Dialog
		:options="{ title: `Apply a patch to ${app?.title}`, position: 'top' }"
		v-model="show"
	>
		<template v-slot:body-content>
			<div class="flex flex-col gap-4">
				<p class="text-base text-gray-600">
					You can select the app patch by either entering the patch URL, or by
					selecting a patch file.
				</p>
				<div class="flex items-end gap-1">
					<FormControl
						v-if="!patch"
						class="w-full"
						label="Patch URL"
						type="data"
						v-model="patchURL"
						variant="outline"
						placeholder="Enter patch URL"
					/>
					<FormControl
						v-else
						class="w-full"
						label="Patch File Name"
						type="data"
						variant="outline"
						v-model="patchFileName"
						placeholder="Set patch file name"
					/>

					<!-- File Selector -->
					<input
						ref="fileSelector"
						type="file"
						:accept="['text/x-patch', 'text/x-diff', 'application/x-patch']"
						class="hidden"
						@change="onPatchFileSelect"
					/>
					<Button @click="$refs.fileSelector.click()" title="Select patch file">
						<FeatherIcon name="file-text" class="h-5 w-5 text-gray-600" />
					</Button>

					<!-- Clear Patch File -->
					<Button @click="clearPatchFile" v-if="patch" title="Clear patch file">
						<FeatherIcon name="x" class="h-5 w-5 text-gray-600" />
					</Button>
				</div>
				<ErrorMessage class="-mt-2 w-full" :message="error" />
				<h3 class="mt-4 text-base font-semibold">Patch Config</h3>
				<FormControl
					v-if="!applyToAllBenches"
					v-model="applyToBench"
					label="Select deploy"
					type="select"
					placeholder="Select a deploy"
					:options="$resources.benches.data"
				/>
				<FormControl
					label="Apply patch to all active deploys"
					type="checkbox"
					v-model="applyToAllBenches"
				/>
				<FormControl
					label="Build assets after applying patch"
					type="checkbox"
					v-model="buildAssets"
				/>
			</div>
		</template>
		<template v-slot:actions>
			<Button variant="solid" class="w-full" @click="applyPatch">
				Apply Patch
			</Button>
		</template>
	</Dialog>
</template>
<script>
import {
	Button,
	Dialog,
	ErrorMessage,
	FeatherIcon,
	FileUploader,
	FormControl
} from 'frappe-ui';

export default {
	name: 'PatchAppDialog',
	props: {
		app: [null, Object],
		bench: String
	},
	components: {
		Dialog,
		FormControl,
		ErrorMessage,
		FileUploader,
		Button,
		FeatherIcon
	},
	watch: {
		app(value) {
			this.show = !!value;
		},
		show(value) {
			this.error = '';
			if (value) {
				return;
			}

			setTimeout(this.clearApp, 150);
		}
	},
	data() {
		return {
			show: false,
			error: '',
			patch: '',
			patchURL: '',
			patchFileName: '',
			buildAssets: false,
			applyToBench: '',
			applyToAllBenches: false
		};
	},
	methods: {
		clearApp() {
			this.$emit('clear-app-to-patch');
		},
		validate() {
			if (!this.$resources.benches.data.length) {
				this.error = 'This bench has no deploys, patch cannot be applied.';
				return false;
			}

			if (this.patch && !this.patchFileName) {
				this.error = 'Please enter a patch file Name.';
				return false;
			}

			if (!this.patch && !this.patchURL) {
				this.error = 'Please enter the patch URL or select a patch file.';
				return false;
			}

			if (!this.applyToAllBenches && !this.applyToBench) {
				this.error =
					'Please select a deploy or check Apply patch to all active deploys.';
				return false;
			}

			return true;
		},
		applyPatch() {
			if (!this.validate()) {
				return;
			}

			if (!this.patchFileName.endsWith('.patch')) {
				this.patchFileName += '.patch';
			}

			const args = {
				name: this.bench,
				app: this.app.name,
				update_data: {
					patch: this.patch,
					patch_filename: this.patchFileName,
					patch_url: this.patchURL,
					build_assets: this.buildAssets,
					patch_bench: this.applyToBench,
					patch_all_benches: this.applyToAllBenches
				}
			};

			this.$resources.applyPatch.submit(args);
		},
		async onPatchFileSelect(e) {
			this.error = '';
			const file = e.target.files?.[0];
			if (!file) {
				return;
			}

			this.patch = await file.text();
			this.patchFileName = file.name;
		},
		clearPatchFile() {
			this.error = '';
			this.patch = '';
			this.patchFileName = '';
		}
	},
	resources: {
		benches() {
			return {
				type: 'list',
				doctype: 'Bench',
				fields: ['name'],
				filters: {
					group: this.bench,
					status: 'Active'
				},
				auto: true,
				onSuccess(data) {
					if (data.length > 0) {
						return;
					}

					this.error = 'This bench has no deploys, patch cannot be applied.';
				},
				onError(data) {
					this.error = data;
				},
				transform(data) {
					return data.map(({ name }) => ({ value: name, label: name }));
				}
			};
		},
		applyPatch() {
			return {
				url: 'press.api.bench.apply_patch',
				onSuccess(data) {
					// TODO: Handle success
					console.log('Patch Success', data);
				},
				onError(data) {
					// TODO: Handle error
					console.log('Patch Error', data);
					this.error = data;
				}
			};
		}
	}
};
</script>
