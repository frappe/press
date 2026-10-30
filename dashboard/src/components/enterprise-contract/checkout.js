// Where Stripe or Razorpay sends the customer back after checkout.
export function contractsReturnUrl() {
	return `${window.location.origin}/dashboard/contracts`
}

// Query params Stripe or Razorpay add on that return URL.
export function isGatewayReturn(query) {
	return Boolean(query.session_id || query.razorpay_payment_link_id)
}
