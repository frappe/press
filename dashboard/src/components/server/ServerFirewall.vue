<template>
	<div>
		<div
			class="bg-yellow-100 px-4 py-3 mb-3 rounded-md border border-yellow-200"
		>
			<p class="text-base space-y-2 leading-relaxed">
				Please note that mis-configuring firewall rules can lead to loss of
				access and should be done with caution. It may take a few minutes for
				changes to take effect.
			</p>
		</div>
		<div class="flex items-center justify-between">
			<Switch
				label="Enabled"
				class="border w-60"
				:disabled="server.get.loading"
				:modelValue="server.doc.firewall_enabled"
				@update:model-value="
					(enabled) => (server.doc.firewall_enabled = enabled)
				"
			/>
			<div class="flex justify-center gap-2">
				<Button
					label="Restore"
					icon-left="trash-2"
					theme="red"
					:disabled="!server.isDirty"
					@click.stop.prevent="() => server.reload()"
				/>
				<Button
					label="Save"
					icon-left="save"
					theme="green"
					:disabled="!server.isDirty"
					@click.stop.prevent="() => server.save.submit()"
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
			:options="{
				data: () => server.doc.firewall_rules,
				columns: [
					{ label: 'Source', fieldname: 'source' },
					{ label: 'Destination', fieldname: 'destination' },
					{ label: 'Protocol', fieldname: 'protocol' },
					{ label: 'Action', fieldname: 'action' },
				],
				rowActions: ({ row }: any) => [
					{
						label: 'Remove',
						onClick: () => {
							server.doc.firewall_rules = server.doc.firewall_rules.filter(
								(rule: any) =>
									!(
										rule.source === row.source &&
										rule.destination === row.destination &&
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
			@submit="(values) => server.doc.firewall_rules.push({ ...values })"
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

const server = createDocumentResource({
	doctype: 'Server',
	name: props.id,
	auto: true,
	cache: ['Server', 'Firewall', props.id],
});
</script>
