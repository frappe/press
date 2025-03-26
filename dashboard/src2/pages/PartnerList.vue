<template>
	<div class="p-4">
		<ObjectList :options="partnerTeams" />
	</div>
</template>
<script>
import ObjectList from '../components/ObjectList.vue';
export default {
	name: 'PartnerList',
	components: {
		ObjectList,
	},
	data() {
		return {};
	},
	computed: {
		partnerTeams() {
			return {
				resource() {
					return {
						url: 'press.api.partner.get_partner_teams',
						transform(data) {
							return data.map((d) => {
								return {
									company: d.billing_name,
									email: d.partner_email,
									country: d.country,
									tier: d.partner_tier || '',
								};
							});
						},
						initialData: [],
						auto: true,
					};
				},
				columns: [
					{
						label: 'Company',
						fieldname: 'company',
					},
					{
						label: 'Partner Email',
						fieldname: 'email',
					},
					{
						label: 'Country',
						fieldname: 'country',
					},
					{
						label: 'Tier',
						fieldname: 'tier',
					},
				],
				onRowClick(row) {
					console.log('clicked', row);
				},
			};
		},
	},
};
</script>
