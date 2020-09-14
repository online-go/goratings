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

export function rankString(r:number, with_tenths?:boolean) {
    let rs:string | number = r;

    if (r < 30) {
        if (with_tenths) {
            rs = (Math.ceil((30 - r) * 10) / 10).toFixed(1);
        } else {
            rs = Math.ceil(30 - r);
        }

        return `${rs}k`;
    }

    if (with_tenths) {
        rs = (Math.floor((r - 29) * 10) / 10).toFixed(1);
    } else {
        rs = Math.floor(r - 29);
    }

    return `${rs}d`;
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
