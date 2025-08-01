export default {
	extends: ['@commitlint/config-conventional'],
	rules: {
		'header-max-length': [2, 'always', 72],
		'subject-case': [2, 'always', 'sentence-case'],
		'scope-case': [2, 'always', 'kebab-case'],
		'body-case': [2, 'always', 'sentence-case'],
		'body-leading-blank': [2, 'always'],
		'footer-leading-blank': [2, 'always'],
	},
};
