# Prints the busy CPU percentage over one second, for pt-stalk to compare with --threshold
trg_plugin() {
    vmstat 1 2 | tail -n 1 | awk '{ print 100 - $15 }'
}
