export function storageGet(key: string, _default: any):any {
    try {
        let item = localStorage.getItem(`visualizer.${key}`);
        if (item) {
            return JSON.parse(item);
        }
    } catch (e) {
        //
    }
    return _default;
}

export function storageSet(key: string, value: any):any {
    localStorage.setItem(`visualizer.${key}`, JSON.stringify(value));
    let item = localStorage.getItem(`visualizer.${key}`);
    if (item) {
        return JSON.parse(item);
    }
    return value;
}

export function rankString(r:number) {
    if (r < 30) {
        r = Math.ceil(30 - r);
        return `${r}k`;
    }

    r = Math.floor(r - 29);
    return `${r}d`;
}

export function humanNumber(n:number) {
  if (Math.abs(n) < 1000) {
    return n;
  }

  const units = ['K', 'M'];
  let u = -1;
  const r = 10**1;

  do {
    n /= 1000;
    ++u;
  } while (Math.round(Math.abs(n) * r) / r >= 1000 && u < units.length - 1);


  return n.toFixed(1) + ' ' + units[u];
}
