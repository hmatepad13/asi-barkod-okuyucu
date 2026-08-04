import assert from "node:assert/strict";
import test from "node:test";

import { vaccineNameForBarcode } from "../app/vaccineCatalog.ts";

test("GS1 DataMatrix içindeki GTIN ile aşı adını bulur", () => {
  assert.equal(
    vaccineNameForBarcode("010868364221007921ABC"),
    "Hepatit A",
  );
});

test("semboloji öneki ve parantezli 01 biçimini destekler", () => {
  assert.equal(vaccineNameForBarcode("]d20108699839968067XYZ"), "MMR");
  assert.equal(vaccineNameForBarcode("(01)08699839960542XYZ"), "BCG");
});

test("katalogda olmayan barkod için ad uydurmaz", () => {
  assert.equal(vaccineNameForBarcode("010000000000000021ABC"), null);
  assert.equal(vaccineNameForBarcode("geçersiz"), null);
});
