module.exports = {
  plugins: [
    "@semantic-release/commit-analyzer",
    "@semantic-release/release-notes-generator",
    ["@semantic-release/exec", {
      // Truncate notes before they're passed to the github plugin
      generateNotesCmd: "echo '${nextRelease.notes}' | head -c 120000"
    }],
    "@semantic-release/github",
  ]
};