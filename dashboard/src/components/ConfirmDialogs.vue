<template>
	<div>
		<Dialog
			:title="dialog.title"
			v-for="dialog in confirmDialogs"
			v-model="dialog.show"
			@close="removeConfirmDialog(dialog)"
			:key="dialog.id"
		>
			<div class="prose">
				<p class="text-base" v-html="dialog.message"></p>
			</div>
			<ErrorMessage
				class="mt-2"
				v-if="dialog.resource"
				:error="dialog.resource.error"
			/>
			<Input
				v-if="dialog.textBox"
				type="textarea"
				class="mt-2"
				v-model="textBoxInput"
				required
			/>
			<template slot="actions">
				<Button type="secondary" @click="removeConfirmDialog(dialog)">
					Cancel
				</Button>
				<Button
					class="ml-2"
					:type="dialog.actionType || 'primary'"
					@click="onDialogAction(dialog)"
					:loading="dialog.resource && dialog.resource.loading"
				>
					{{ dialog.actionLabel || 'Submit' }}
				</Button>
			</template>
		</Dialog>
	</div>
</template>
<script>
import Vue from 'vue';

export default {
	name: 'ConfirmDialogs',
	data() {
		return {
			confirmDialogs: [],
			textBoxInput: null
		};
	},
	created() {
		Vue.prototype.$confirm = this.confirm;
	},
	methods: {
		confirm(dialog) {
			dialog.id = this.confirmDialogs.length;
			dialog.show = true;
			if (dialog.resource) {
				dialog.resource.on('onSuccess', () => {
					this.removeConfirmDialog(dialog);
				});
			}
			this.confirmDialogs.push(dialog);
		},
		onDialogAction(dialog) {
			let closeDialog = () => this.removeConfirmDialog(dialog);
			dialog.action(closeDialog, this.textBoxInput);
		},
		removeConfirmDialog(dialog) {
			this.confirmDialogs = this.confirmDialogs.filter(
				_dialog => dialog !== _dialog
			);
		}
	}
};
</script>
