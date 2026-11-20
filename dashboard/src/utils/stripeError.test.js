import { describe, expect, it } from 'vitest'
import { getStripeErrorMessage } from './stripeError'

describe('getStripeErrorMessage', () => {
	it('explains card_velocity_exceeded as a bank limit, not as repeated attempts', () => {
		const message = getStripeErrorMessage({
			decline_code: 'card_velocity_exceeded',
			message:
				'Your card was declined for making repeated attempts too frequently.',
		})
		expect(message).toContain('reached a limit set by your bank')
		expect(message).not.toContain('repeated attempts')
	})

	it('keeps the Stripe message for a decline code without a mapping', () => {
		const error = {
			decline_code: 'expired_card',
			message: 'Your card has expired.',
		}
		expect(getStripeErrorMessage(error)).toBe('Your card has expired.')
	})

	it('keeps the Stripe message for an error without a decline code', () => {
		const error = { message: 'Your card number is incorrect.' }
		expect(getStripeErrorMessage(error)).toBe('Your card number is incorrect.')
	})
})
