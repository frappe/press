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
			if (!this.failedStep || !this.failedStep.title) {
				return 'Build Failed';
			}

			return `Build Step Failed - "${this.failedStep.title}"`;
		},
		body(): string {
			let splits = this.build_error
				.trim()
				.split('\n')
				.map(s => s.trim());
			let command = this.failedStep?.command ?? '';

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
				command = command || parseStageLine(splits[0]);
				splits = splits.slice(1);
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

			// Incase stage line lies after error body
			const out = getCommandAndSplits(splits);
			splits = out.splits;

			if (!command) {
				command = out.command;
			}

			let output = splits.map(s => stripLinePrefix(s)).join('\n');
			if (command) {
				return `# Step Command\n${command}\n\n# Step Output\n${output}\n`;
			}

			return output;
		},
		failedStep() {
			for (const step of this.build_steps ?? []) {
				if (step.status === 'Failure') return step;
			}

			return null;
		}
	}
});

function getCommandAndSplits(splits: string[]): {
	command: string;
	splits: string[];
} {
	let command = '';
	for (let i = 0; i < splits.length; i++) {
		const line = splits[i];
		if (!line.startsWith('> [stage-')) continue;

		command = parseStageLine(line);
		const index = i - 2;
		if (index <= 0) {
			break;
		}

		splits = splits.slice(0, index);
	}

	return { command, splits };
}

function stripLinePrefix(line: string): string {
	// Match example: "#35 2.678 "
	const match = line.match(/^(#\d+\s)?\d+\.\d+\s?/)?.[0];
	if (!match) {
		return line;
	}

	return line.split(match)[1].trimEnd();
}

function parseStageLine(line: string): string {
	let splits = line.split(/\[stage-[^]+\]/);
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
