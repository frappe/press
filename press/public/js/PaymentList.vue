<template>
	<div>
		<div>
			<div>Payments</div>
			<div>{{ payments.length }}</div>
		</div>
		<div v-for="payment in payments" v-bind:key="payment.name">
			<div>{{ payment.name }}</div>
			<div>{{ payment.amount }}</div>
			<div>{{ payment.balance }}</div>
			<div>{{ payment.date }}</div>
		</div>
	</div>
</template>

<script>
export default {
	name: "SiteList",
	data() {
		return {
			payments: [
				{
					name: "PAYMENT-002",
					amount: "10 USD",
					balance: "110 USD",
					date: "2019-11-27T03:24:00"
				},
				{
					name: "PAYMENT-001",
					amount: "100 USD",
					balance: "100 USD",
					date: "2019-11-26T03:24:00"
				}
			]
		};
	}
};
</script>
