<template>
	<div
		class="max-w-3xl divide-y sm:rounded sm:border sm:p-5"
		v-if="$site?.doc?.actions"
	>
		<div
			class="py-3 first:pt-0 last:pb-0"
			v-for="row in $site.doc.actions"
			:key="row.action"
		>
			<SiteActionCell
				:siteName="site"
				:actionLabel="row.action"
				:method="row.doc_method"
				:description="row.description"
				:buttonLabel="row.button_label"
			/>
		</div>
	</div>
</template>
<script>
import { getCachedDocumentResource } from 'frappe-ui';
import SiteActionCell from './SiteActionCell.vue';

export default {
	name: 'SiteActions',
	props: ['site'],
	components: { SiteActionCell },
	computed: {
		$site() {
			return getCachedDocumentResource('Site', this.site);
		}
	}
};
</script>
