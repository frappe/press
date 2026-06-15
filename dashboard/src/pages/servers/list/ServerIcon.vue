<script setup lang="ts">
import HetnzerLogo from '@/logo/Hetzner.vue'
import FrappeLogo from '@/logo/Frappe.vue'
import AwsLogo from '@/logo/Aws.vue'
import OracleLogo from '@/logo/Oracle.vue'
import DigitalOceanLogo from '@/logo/DigitalOcean.vue'

const providerIcons = {
	'Frappe Compute': FrappeLogo,
	Generic: FrappeLogo,
	Hetzner: HetnzerLogo,
	'AWS EC2': AwsLogo,
	Oracle: OracleLogo,
	DigitalOcean: DigitalOceanLogo,
}

interface Props {
	provider: string
}

const props = defineProps<Props>()
</script>

<template>
	<component :is="providerIcons[provider]" class="size-4" />
</template>
