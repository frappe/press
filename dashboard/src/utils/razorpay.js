let razorpayScriptPromise = null;

export function loadRazorpayScript() {
	if (window.Razorpay) return Promise.resolve();
	if (!razorpayScriptPromise) {
		razorpayScriptPromise = new Promise((resolve, reject) => {
			const script = document.createElement('script');
			script.src = 'https://checkout.razorpay.com/v1/checkout.js';
			script.onload = resolve;
			script.onerror = () => {
				razorpayScriptPromise = null; // allow retry on next call
				reject(new Error('Failed to load Razorpay checkout script'));
			};
			document.head.appendChild(script);
		});
	}
	return razorpayScriptPromise;
}
