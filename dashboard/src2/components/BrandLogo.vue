<template>
	<span v-if="type == 'header'">
		<img
			v-if="brandDetails && brandDetails.brand_logo"
			:src="brandDetails.brand_logo"
			class="inline-block h-7 w-7"
		/>
		<FCLogo class="inline-block h-7 w-7" v-else />
	</span>

	<span v-else-if="type == 'footer'">
		<img
			v-if="brandDetails && brandDetails.footer_logo"
			:src="brandDetails.footer_logo"
			class="h-4"
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
	props: {
		type: {
			type: String
		}
	},
	computed: {
		brandDetails() {
			return getBrandInfo();
		}
	}
};
</script>
