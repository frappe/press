const camelCaseToWords = (str:string) => {
  const result = str.replace(/([a-z])([A-Z])/g, '$1 $2');
  return result;
}

const includesIgnoreCase = (arr, value) =>{
  if (!value) return false;
  return arr.some(item => item?.toLowerCase() === value.toLowerCase());
}

export const formatLabels = (data) => {
const assorted = {}

let tmp = []

  tmp = data.filter(x => !x.path.includes(':'))

  tmp = tmp.map(x => ({ name: camelCaseToWords(x.name), path: x.path }))

  tmp.forEach(x => {
    const splits = x.path.split('/')
    let group = splits[1]

    if(assorted[group] && splits.length > 3) group = splits[2]
    

    if (!assorted[group]) assorted[group] = []

    // remove first word
    const split_title = x.name.split(" ")
    const split_group = group.split("-")

    let title =   includesIgnoreCase(split_group, split_title[0])?    split_title.slice(1).join(" "):x.name 

    if(title !== '')

    assorted[group].push( { name: title, route: x.path})
  })


  for (const [key, value] of Object.entries(assorted)) {
    if(value.length == 0 || key === '') {
      delete assorted[key]
    }
  }

  return assorted
}

export const filterLabels = (data, query) => {
  if (!query) return data

  const q = query.toLowerCase()
  const result = {}

  for (const [group, items] of Object.entries(data)) {
    if (group.toLowerCase().includes(q)) {
      result[group] = items
      continue
    }

    const filtered = items.filter(item =>
      item.name.toLowerCase().includes(q)
    )

    if (filtered.length) result[group] = filtered
  }

  return result
}
