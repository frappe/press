// Shared plan types run on shared CPU, so we support them only in part. The
// backend has no flag for it, so we go by the title the plan type carries.
export function isSharedPlanType(title?: string): boolean {
	return /shared/i.test(title ?? '')
}
