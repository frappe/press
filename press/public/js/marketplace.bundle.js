import Fuse from 'fuse.js';

const allAppCardNodes = document.getElementsByClassName('app-card');
const searchInput = document.getElementById('app-search-input');
const noResultsMessage = document.getElementById('no-results-message');

const appList = [];
for (let node of allAppCardNodes) {
	appList.push({
		title: node.getAttribute('data-title'),
		description: node.getAttribute('data-description'),
		name: node.id,
	});
}

// Initialize fuse.js
const options = {
	keys: ['title'], // Can add description later if required
};
const fuse = new Fuse(appList, options);

searchInput.addEventListener('input', (e) => {
	// TODO: Debounce/Throttle
	const searchText = e.target.value;
	if (!searchText) {
		displayAllApps();
		return;
	}

	const results = fuse.search(searchText);
	updateAppList(results);
});

function updateAppList(results) {
	for (let node of allAppCardNodes) {
		node.style.display = 'none';
	}

	if (results.length === 0) {
		noResultsMessage.style.display = '';
		return;
	} else {
		noResultsMessage.style.display = 'none';
	}

	for (let result of results) {
		allAppCardNodes[result.refIndex].style.display = '';
	}
}

function displayAllApps() {
	noResultsMessage.style.display = 'none';
	for (let node of allAppCardNodes) {
		node.style.display = '';
	}
}
