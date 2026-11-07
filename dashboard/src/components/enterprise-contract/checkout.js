// Where Stripe sends the customer back after checkout.
export function contractsReturnUrl() {
	return `${window.location.origin}/dashboard/contracts`
}

// Query param Stripe adds on that return URL.
export function isGatewayReturn(query) {
	return Boolean(query.session_id)
}
