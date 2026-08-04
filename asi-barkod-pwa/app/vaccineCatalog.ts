const VACCINE_NAMES: Readonly<Record<string, string>> = {
  "08681308966315": "KPA",
  "08683642210079": "Hepatit A",
  "08683642210086": "Su çiçeği",
  "08699625770041": "Tdab",
  "08699625960343": "TETRAXIM",
  "08699625960527": "Hexaxim",
  "08699839339010": "OPA",
  "08699839960542": "BCG",
  "08699839961105": "Td",
  "08699839968012": "Hepatit B",
  "08699839968067": "MMR",
  "18681308966312": "KPA",
  "18683642210076": "Hepatit A",
  "18683642210083": "Su çiçeği",
  "18699625960340": "TETRAXIM",
  "18699625960524": "Hexaxim",
  "18699839961102": "Td",
  "18699839968019": "Hepatit B",
  "28699839968061": "MMR",
};

const GTIN_PATTERN = /^(?:\][A-Za-z0-9]{2})?(?:\(01\)|01)(\d{14})/;

export function vaccineNameForBarcode(raw: string): string | null {
  const match = GTIN_PATTERN.exec(raw.trim());
  return match ? VACCINE_NAMES[match[1]] ?? null : null;
}
