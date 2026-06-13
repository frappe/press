<template>
	<Dialog v-model="show" title="Configure Auto Update">
		<div class="mt-8">
			<Switch
				v-model="enableAutoUpdate"
				label="Enable Auto Update"
				description="Automatically schedule site updates whenever available"
			/>
		</div>
	</Dialog>
</template>

<script>
import { Switch, getCachedDocumentResource } from 'frappe-ui'

export default {
	props: {
		site: {
			type: String,
			required: true,
		},
	},
	components: { Switch },
	data() {
		return {
			show: true,
		}
	},
	computed: {
		$site() {
			return getCachedDocumentResource('Site', this.site)
		},
		enableAutoUpdate: {
			get() {
				return !this.$site?.doc.skip_auto_updates
			},
			set(value) {
				this.$site.setValue.submit({ skip_auto_updates: !value })
			},
		},
	},
}
</script>
