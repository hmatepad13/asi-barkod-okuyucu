export type Receiver = {
  id: string;
  name: string;
  online: boolean;
  lastSeen: number;
  cloud: boolean;
};

export function mergeReceiver(
  current: Receiver | undefined,
  incoming: Receiver,
): Receiver {
  if (!current) return incoming;
  return {
    id: incoming.id,
    name: incoming.name || current.name,
    online: current.online || incoming.online,
    lastSeen: Math.max(current.lastSeen, incoming.lastSeen),
    cloud: current.cloud || incoming.cloud,
  };
}

export function receiverConnectionLabel(receiver: Receiver): string {
  return receiver.cloud ? "Ably üzerinden" : "Bağlantı yok";
}
