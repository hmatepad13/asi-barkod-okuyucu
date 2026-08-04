import assert from "node:assert/strict";
import test from "node:test";

import {
  mergeReceiver,
  receiverConnectionLabel,
  type Receiver,
} from "../app/receiverTransport.ts";

const cloudReceiver: Receiver = {
  id: "pc-1",
  name: "HASTAKABUL",
  online: true,
  lastSeen: 100,
  cloud: true,
};

test("aynı PC'nin Ably kayıtlarını tek satırda birleştirir", () => {
  const merged = mergeReceiver(cloudReceiver, {
    ...cloudReceiver,
    lastSeen: 120,
  });

  assert.equal(merged.cloud, true);
  assert.equal(receiverConnectionLabel(merged), "Ably üzerinden");
});

test("Ably olmayan alıcıyı bağlantısız gösterir", () => {
  assert.equal(receiverConnectionLabel(cloudReceiver), "Ably üzerinden");
  assert.equal(
    receiverConnectionLabel({
      ...cloudReceiver,
      cloud: false,
    }),
    "Bağlantı yok",
  );
});
