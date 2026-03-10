<template>
	<div>
		<div
			class="bg-yellow-100 text-yellow-900 px-4 py-3 mb-3 rounded-md border border-yellow-200"
		>
			<p class="text-base space-y-2 leading-relaxed">
				Please note that mis-configuring firewall rules can lead to loss of
				access and should be done with caution. It may take a few minutes for
				changes to take effect.
			</p>
		</div>
		<div v-if="firewall.doc" class="flex items-center justify-between">
			<Switch
				label="Enabled"
				class="border w-60"
				v-model="firewall.doc.enabled"
				:disabled="firewall.get.loading"
			/>
			<div class="flex justify-center gap-2">
				<Button
					label="Discard"
					icon-left="trash-2"
					theme="gray"
					:disabled="!firewall.isDirty"
					@click.stop.prevent="() => firewall.reload()"
				/>
				<Button
					label="Save"
					icon-left="save"
					theme="green"
					:disabled="!firewall.isDirty"
					@click.stop.prevent="() => firewall.save.submit()"
				/>
				<Button
					label="Add Rule"
					icon-left="plus"
					variant="solid"
					@click="openAddDialog = !openAddDialog"
				/>
			</div>
		</div>
		<ObjectList
			v-if="firewall.doc"
			:options="{
				data: () => firewall.doc.rules,
				columns: [
					{
						label: 'Source',
						fieldname: 'source',
						format: (value: string) => value || '—',
					},
					{
						label: 'Port',
						fieldname: 'port',
						format: (value: string) => value || '—',
					},
					{ label: 'Protocol', fieldname: 'protocol' },
					{ label: 'Action', fieldname: 'action' },
					{
						label: '',
						format: (_: any, row: any) => {
							if (row.name) {
								return '';
							}
							return 'Unsaved';
						},
						type: 'Badge',
						theme: 'orange',
						width: '100px',
					},
				],
				rowActions: ({ row }: any) => [
					{
						label: 'Remove',
						onClick: () => {
							firewall.doc.rules = firewall.doc.rules.filter(
								(rule: any) =>
									!(
										rule.source === row.source &&
										rule.port === row.port &&
										rule.protocol === row.protocol &&
										rule.action === row.action
									),
							);
						},
					},
				],
			}"
		/>
		<ServerFirewallDialog
			v-model="openAddDialog"
			@submit="(values) => firewall.doc.rules.push({ ...values })"
		/>
	</div>
</template>

<script setup lang="ts">
import { createDocumentResource, Switch } from 'frappe-ui';
import ObjectList from '../../components/ObjectList.vue';
import ServerFirewallDialog from './ServerFirewallDialog.vue';
import { ref } from 'vue';

const props = defineProps<{
	id: string;
}>();

const openAddDialog = ref(false);

const firewall = createDocumentResource({
	doctype: 'Server Firewall',
	name: props.id,
	auto: true,
	cache: ['Server', 'Firewall', props.id],
});
</script>
