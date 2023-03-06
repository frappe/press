<script setup>
import { getCurrentInstance, ref } from 'vue';

const app = getCurrentInstance();
const confirmDialogs = ref([]);

function confirm(dialog) {
	dialog.id = confirmDialogs.value.length;
	dialog.show = true;
	if (dialog.resource) {
		dialog.resource.on('onSuccess', () => {
			removeConfirmDialog(dialog);
		});
	}
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
			:options="{ title: dialog.title }"
		>
			<template v-slot:body-content>
				<div class="prose">
					<p class="text-base" v-html="dialog.message"></p>
				</div>
				<ErrorMessage
					class="mt-2"
					v-if="dialog.resource"
					:error="dialog.resource.error"
				/>
			</template>

			<template v-slot:actions>
				<Button appearance="secondary" @click="removeConfirmDialog(dialog)">
					Cancel
				</Button>
				<Button
					class="ml-2"
					:appearance="dialog.actionType || 'primary'"
					@click="onDialogAction(dialog)"
					:loading="dialog.resource && dialog.resource.loading"
				>
					{{ dialog.actionLabel || 'Submit' }}
				</Button>
			</template>
		</Dialog>
	</div>
</template>
