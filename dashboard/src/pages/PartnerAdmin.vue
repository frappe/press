<template>
	<div class="sticky top-0 z-10 shrink-0">
		<Header>
			<Breadcrumbs
				:items="[{ label: 'Partner Admin', route: '/partner-admin' }]"
			/>
		</Header>
		<TabsWithRouter v-if="$team?.doc?.is_desk_user" :tabs="tabs" />
		<div
			v-else
			class="mx-auto mt-60 w-fit rounded border border-dashed px-12 py-8 text-center text-gray-600"
		>
			<lucide-alert-triangle class="mx-auto mb-4 h-6 w-6 text-red-600" />
			<ErrorMessage message="You aren't permitted to view the billing page" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { getTeam } from '@/data/team';
import { Breadcrumbs } from 'frappe-ui';
import Header from '@/components/Header.vue';
import TabsWithRouter from '@/components/TabsWithRouter.vue';
import LucideAlertTriangle from '~icons/lucide/alert-triangle';

const $team = getTeam();
defineOptions({ name: 'PartnerAdmin' });

const tabs = [
	{ label: 'Partner', route: { name: 'PartnerList' } },
	{ label: 'Certificates', route: { name: 'CertificateList' } },
	{ label: 'Leads', route: { name: 'PartnerAdminLeads' } },
	{ label: 'Resources', route: { name: 'PartnerAdminResources' } },
];
</script>
