<template>
	<Dialog v-model="show" :options="{ title: 'Pass to Another Partner' }">
		<template #body-content>
			<div class="flex flex-col gap-5">
				<FormControl
					v-model="partner"
					label="Select Partner"
					type="select"
					name="partner"
					:options="partnerList.data || []"
				/>
				<Button variant="solid" @click="() => changePartner.submit()"
					>Submit</Button
				>
			</div>
		</template>
	</Dialog>
</template>
<script setup>
import { Dialog, FormControl, createResource } from 'frappe-ui';
import { defineEmits, ref } from 'vue';
import { toast } from 'vue-sonner';

const show = defineModel();
const partner = ref();
const emit = defineEmits(['update']);
const props = defineProps({
	lead_id: {
		type: String,
		required: true,
	},
});

const changePartner = createResource({
	url: 'press.api.partner.change_partner',
	makeParams: () => {
		return {
			lead_name: props.lead_id,
			partner: partner.value,
		};
	},
	onSuccess: () => {
		emit('update');
		show.value = false;
	},
	onError: (err) => {
		toast.error(err.message);
	},
});

const partnerList = createResource({
	url: 'press.api.partner.get_partner_teams',
	auto: true,
	cache: 'partnerList',
	transform: (data) => {
		console.log(data);
		return data.map((d) => ({
			label: `${d.billing_name} - ${d.country}`,
			value: d.name,
		}));
	},
});
</script>
