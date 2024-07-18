<template>
	<span v-if="header">
		<img
			v-if="brandDetails && brandDetails.app_logo"
			:src="brandDetails.app_logo"
			class="inline-block h-7 w-7"
		/>
		<FCLogo class="inline-block h-7 w-7" v-else />
	</span>

	<span v-else-if="footer">
		<img
			v-if="brandDetails && brandDetails.app_footer_logo"
			:src="brandDetails.app_footer_logo"
		/>
		<FrappeLogo class="h-4" v-else />
	</span>

	<span v-else> </span>
</template>
<script>
import FCLogo from '@/components/icons/FCLogo.vue';
import FrappeLogo from '@/components/icons/FrappeLogo.vue';
import { getBrandInfo } from '../data/branding';

export default {
	name: 'BrandLogo',
	components: {
		FCLogo,
		FrappeLogo
	},
	props: ['header', 'footer'],
	computed: {
		brandDetails() {
			return getBrandInfo();
		}
	}
};
</script>
