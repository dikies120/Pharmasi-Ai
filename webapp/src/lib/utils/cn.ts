type ClassDictionary = Record<string, boolean | null | undefined>;
type ClassInput =
  | string
  | number
  | null
  | undefined
  | false
  | ClassDictionary
  | ClassInput[];

function walkClassInput(value: ClassInput, result: string[]): void {
  if (!value) {
    return;
  }

  if (typeof value === "string" || typeof value === "number") {
    result.push(String(value));
    return;
  }

  if (Array.isArray(value)) {
    for (const item of value) {
      walkClassInput(item, result);
    }
    return;
  }

  for (const [key, shouldInclude] of Object.entries(value)) {
    if (shouldInclude) {
      result.push(key);
    }
  }
}

export function cn(...inputs: ClassInput[]): string {
  const result: string[] = [];

  for (const input of inputs) {
    walkClassInput(input, result);
  }

  return result.join(" ");
}
