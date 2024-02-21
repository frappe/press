<template>
	<Dialog
		:options="{ title: `Apply patch to ${app?.title}`, position: 'top' }"
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
			buildAssets: false
		};
	},
	methods: {
		/**
		 * TODO:
		 * - Enter URL for patchfile
		 * - Select patchfile from local
		 * - Set patch file name
		 * - Apply patch
		 * - Store patch in doctype and trigger agent job on insert
		 * - Display if app has been patched in apps list
		 * - Option to undo patches if app has patch
		 */
		clearApp() {
			this.$emit('clear-app-to-patch');
		},
		applyPatch() {
			if (this.patch && !this.patchFileName) {
				this.error = 'Please set a Patch File Name.';
				return;
			}

			if (!this.patch && !this.patchURL) {
				this.error = 'Please set patch URL or select a patch file.';
				return;
			}

			if (!this.patchFileName.endsWith('.patch')) {
				this.patchFileName += '.patch';
			}

			this.$resources.applyPatch.submit({
				name: this.bench,
				app: app.name,
				update_data: {
					patch: this.patch,
					patch_filename: this.patchFileName,
					patch_url: this.patchURL,
					build_assets: this.buildAssets
				}
			});
		},
		async onPatchFileSelect(e) {
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
		applyPatch() {
			return {
				url: 'press.api.bench.patch_app',
				onSuccess(data) {
					console.log('Patch Success', data);
				},
				onError(data) {
					this.error = data;
				}
			};
		}
	}
};
</script>
