export const filterLabels = (data, query) => {
  const q = query.toLowerCase()
  const result = {}

  // used for flat index
  let index = 0

  for (const [group, v] of Object.entries(data)) {
    if (group.toLowerCase().includes(q)) {
      result[group] = {
        items: v.items.map(item => ({
          ...item,
          flatindex: index++
        }))
      }
      continue
    }

    const filtered = v.items.filter(item =>
      item.name.toLowerCase().includes(q)
    )

    if (filtered.length) {
      result[group] = {
        items: filtered.map(item => ({
          ...item,
          flatindex: index++
        }))
      }
    }
  }

  return result
}
