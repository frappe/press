export class DashboardError extends Error {
	constructor(message: string) {
		super(message);
		this.name = 'DashboardError';
	}
}
