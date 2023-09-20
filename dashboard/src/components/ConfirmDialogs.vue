<script setup>
import { getCurrentInstance, ref } from 'vue';

const app = getCurrentInstance();
const confirmDialogs = ref([]);

function confirm(dialog) {
	dialog.id = confirmDialogs.value.length;
	dialog.show = true;
	confirmDialogs.value.push(dialog);
}

function removeConfirmDialog(dialog) {
	confirmDialogs.value = confirmDialogs.value.filter(
		_dialog => dialog !== _dialog
	);
}

function onDialogAction(dialog) {
	let closeDialog = () => removeConfirmDialog(dialog);
	dialog.action(closeDialog);
}

app.appContext.config.globalProperties.$confirm = confirm;
</script>

<template>
	<div>
		<Dialog
			v-for="dialog in confirmDialogs"
			v-model="dialog.show"
			@close="removeConfirmDialog(dialog)"
			:key="dialog.id"
			:options="{
				title: dialog.title,
				actions: [
					{
						label: dialog.actionLabel || 'Submit',
						theme: dialog.actionColor,
						variant: dialog.actionVariant || 'solid',
						onClick: () => onDialogAction(dialog),
						loading: dialog.resource?.loading
					},
					{
						label: 'Cancel',
						onClick: () => removeConfirmDialog(dialog)
					}
				]
			}"
		>
			<template v-slot:body-content>
				<div class="prose">
					<p class="text-base" v-html="dialog.message"></p>
				</div>
				<ErrorMessage
					class="mt-2"
					v-if="dialog.resource"
					:message="dialog.resource.error"
				/>
			</template>
		</Dialog>
	</div>
</template>
