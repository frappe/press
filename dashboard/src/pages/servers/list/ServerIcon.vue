<script setup lang="ts">
import Hetnzer from '@/logo/Hetzner.vue'
import Frappe from '@/logo/Frappe.vue'
import Aws from '@/logo/Aws.vue'
import Oracle from '@/logo/Oracle.vue'
import DigitalOcean from '@/logo/DigitalOcean.vue'
import Scaleway from '@/logo/Scaleway.vue'

const providerIcons = {
	'Frappe Compute': Frappe,
	Generic: Oracle,
	Hetzner: Hetnzer,
	'AWS EC2': Aws,
	Oracle: Oracle,
	OCI: Oracle,
	DigitalOcean: DigitalOcean,
  Scaleway: Scaleway,
}

interface Props {
	provider: string
}

const props = defineProps<Props>()
</script>

<template>
	<component :is="providerIcons[provider]" class="size-4" />
</template>
