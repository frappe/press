const CONTACT_BANK = 'Please try with another card or contact your bank.'

const DECLINE_MESSAGES = {
	card_velocity_exceeded: `Your card was declined because it reached a limit set by your bank, such as its balance, credit limit or transaction limit. ${CONTACT_BANK}`,
	do_not_honor: `Your card was declined. It might be due to insufficient funds or you might've exceeded your daily limit. ${CONTACT_BANK}`,
	transaction_not_allowed: `Your card was declined. It might be due to restrictions on your card, like international transactions or online payments. ${CONTACT_BANK}`,
}

export function getStripeErrorMessage(error) {
	return DECLINE_MESSAGES[error?.decline_code] || error?.message
}
