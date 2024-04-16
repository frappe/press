<template>
	<FoldStep
		:open="open"
		:title="title"
		:body="body"
		status="Failure"
		@toggle="open = !open"
	/>
</template>
<script lang="ts">
import { defineComponent } from 'vue';
import FoldStep from './FoldStep.vue';

export default defineComponent({
	name: 'BuildError',
	data() {
		return { open: true };
	},
	props: {
		build_error: { type: String, required: true },
		build_steps: { type: Array, required: false }
	},
	components: { FoldStep },
	computed: {
		title(): string {
			if (!this.failedStepTitle) {
				return 'Build Failed';
			}

			return `Build Step Failed - "${this.failedStepTitle}"`;
		},
		body(): string {
			// @ts-ignore
			window.d = this;
			var splits = this.build_error
				.trim()
				.split('\n')
				.map(s => s.trim());

			// Remove first ERROR: line
			if (splits.at(0)?.startsWith('ERROR:')) {
				splits = splits.slice(1);
			}

			// Remove last ERROR: line
			if (splits.at(-1)?.startsWith('ERROR:')) {
				splits = splits.slice(0, -1);
			}

			// Remove error body start delimiter
			if (splits.at(0).startsWith('------')) {
				splits = splits.slice(1);
			}

			// Remove docker output from stage command line
			if (splits.at(0).startsWith('> [stage-')) {
				splits[0] = `# Build Step Command\n${parseStageLine(splits[0])}\n\n`;
				splits[1] = `# Build Step Output\n${stripDurationStamp(splits[1])}`;
			}

			// Remove Dockerfile line end delimiter
			if (splits.at(-1).startsWith('--------------------')) {
				splits = splits.slice(0, -1);
			}

			// Remove error body end delimiter
			const index = splits.findIndex(l => l.startsWith('Dockerfile:'));
			if (index > 0) {
				splits = splits.slice(0, index - 1);
			}

			return splits.map(s => stripDurationStamp(s)).join('\n');
		},
		failedStepTitle(): string {
			for (const step of this.build_steps ?? []) {
				if (step.status === 'Failure') return step.title;
			}

			return '';
		}
	}
});

function stripDurationStamp(line: string): string {
	const match = line.match(/^\d+\.\d+\s/)?.[0];
	if (!match) {
		return line;
	}

	return line.split(match)[1].trim();
}

function parseStageLine(line: string): string {
	var splits = line.split(/\[stage-[^]+\]/);
	if (splits.length < 2) {
		return line;
	}

	splits = splits[1]
		.trim()
		.split(' ')
		.map(s => s.trim())
		.filter(s => s.length);
	if (splits.length < 2) {
		return line;
	}

	// Remove Dockerfile command, eg: 'RUN'
	splits = splits.slice(1);

	// Remove Dockerfile command flags, eg: --mount
	while (true) {
		if (splits[0]?.startsWith('--')) {
			splits = splits.slice(1);
		} else break;
	}

	line = splits.join(' ');

	// Remove trailing ':'
	if (line.endsWith(':')) {
		line = line.slice(0, -1);
	}

	return line.split('`#stage-')[0];
}
</script>
