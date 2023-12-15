<template>
	<Dialog
		:options="{
			title: 'Change Plan',
			size: '5xl',
			actions: [
				{
					label: 'Change plan',
					variant: 'solid',
					onClick: changePlan,
					disabled: !plan || ($site?.doc && plan === $site.doc.plan)
				}
			]
		}"
		v-model="show"
	>
		<template #body-content>
			<SitePlansCards v-model="plan" />
			<ErrorMessage class="mt-2" :message="$site.setPlan.error" />
		</template>
	</Dialog>
</template>
<script>
import { getCachedDocumentResource } from 'frappe-ui';
import SitePlansCards from './SitePlansCards.vue';

export default {
	name: 'ManageSitePlansDialog',
	components: { SitePlansCards },
	props: {
		site: {
			type: String,
			required: true
		}
	},
	data() {
		return {
			show: true,
			plan: null
		};
	},
	watch: {
		site: {
			immediate: true,
			handler(siteName) {
				if (siteName) {
					if (this.$site?.doc?.plan) {
						this.plan = this.$site.doc.plan;
					}
				}
			}
		}
	},
	methods: {
		changePlan() {
			return this.$site.setPlan.submit(
				{ plan: this.plan },
				{
					onSuccess: () => {
						this.show = false;
						this.$toast.success(`Plan changed to ${this.$site.doc.plan}`);
					}
				}
			);
		}
	},
	computed: {
		$site() {
			return getCachedDocumentResource('Site', this.site);
		}
	}
};
</script>
