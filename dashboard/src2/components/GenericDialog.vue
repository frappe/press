<template>
	<Dialog :options="options" v-model="show">
		<template v-slot:body-content>
			<slot>
				<GenericDialogField
					v-for="field in fields"
					:key="field.fieldname"
					:field="field"
				/>
			</slot>
		</template>
	</Dialog>
</template>
<script>
import { Dialog } from 'frappe-ui';
import GenericDialogField from './GenericDialogField.vue';

export default {
	name: 'GenericDialog',
	props: ['options', 'fields'],
	components: { Dialog, GenericDialogField },
	data() {
		return {
			show: true
		};
	}
};
</script>
