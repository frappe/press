<template>
	<Dialog v-bind="options" v-model="show">
		<slot>
			<GenericDialogField
				v-for="field in fields"
				:key="field.fieldname"
				:field="field"
			/>
		</slot>
	</Dialog>
</template>
<script>
import { Dialog } from 'frappe-ui'
import GenericDialogField from './GenericDialogField.vue'

export default {
	name: 'GenericDialog',
	props: ['options', 'fields'],
	components: { Dialog, GenericDialogField },
	data() {
		return {
			show: true,
		}
	},
}
</script>
