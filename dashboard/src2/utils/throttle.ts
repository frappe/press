export function throttle(func: Function, wait: number) {
	let timeout = 0;
	let pending = false;

	return (...args: any) => {
		if (timeout) {
			pending = true;
			return;
		}

		func(...args);
		timeout = setTimeout(() => {
			timeout = 0;
			if (pending) {
				func(...args);
				pending = false;
			}
		}, wait);
	};
}
