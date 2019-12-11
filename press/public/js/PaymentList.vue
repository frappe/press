<template>
	<div>
		<div>
			<div>Payments</div>
			<div>{{ payments.length }}</div>
		</div>
		<div v-for="payment in payments" v-bind:key="payment.name">
			<div>{{ payment.name }}</div>
			<div>{{ payment.amount }}</div>
			<div>{{ payment.date }}</div>
			<div><a :href="'/api/method/frappe.utils.print_format.download_pdf?doctype=Payment&name=' + payment.name">Invoice</a></div>
		</div>
	</div>
</template>

<script>
export default {
	name: "SiteList",
	data() {
		return {
			payments: [],
		};
	},
	mounted() {
		this.get();
	},
	methods: {
		get: async function() {
			let response = await fetch("/api/method/press.api.payment.all");
			if (response.ok) {
				const payments = await response.json();
				console.log("Nothing Went Wrong");
				console.log(payments);
				this.payments = payments.message;
			} else {
				console.log("Something Went Wrong");
			}
		}
	}
};
</script>
