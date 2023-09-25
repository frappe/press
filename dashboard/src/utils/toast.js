import { ref } from 'vue';

export const notifications = ref([]);

export const hideNotification = id => {
	notifications.value = notifications.value.filter(props => props.id !== id);
};

export const notify = props => {
	// TODO: remove the line below once the frappe-ui bug (onError triggers twice) is fixed
	if (notifications.value.some(n => n.message === props.message)) return;
	props.id = Math.floor(Math.random() * 1000 + Date.now());
	notifications.value.push(props);
	setTimeout(() => hideNotification(props.id), props.timeout || 5000);
};
