## GPU Credit

### Problem

You're implementing a GPU credit system.

We support three operations:

createGrant(id, amount, ts, expTs)
A block of credits becomes available at time ts and expires at time expTs.

subtract(amount, ts)
Spend credits at timestamp ts, always consuming the earliest-expiring credits first.
If there aren’t enough credits at that moment, subtract itself does not throw.

getBalance(ts)
Return the number of unexpired credits available at exactly time ts.
If at time ts (or any earlier time) a subtract did not have enough credits,
then getBalance(ts) must throw an exception.

### Clarifying questions to ask

“Can events come with timestamps out of order?”

“Should subtract ever throw, or only getBalance(ts) throws when credits are insufficient?”

“When subtracting, do I always consume credits that expire earliest first?”

### Solution

Because both credit grants and subtract operations arrive out of order with arbitrary timestamps,
I cannot update the balance eagerly inside createGrant or subtract.
A later event with an earlier timestamp could completely change what the balance should have been at that time.

So I store every operation as a timestamped event.
When getBalance(ts) is called, I reconstruct the state by replaying all events with timestamp ≤ ts in chronological order.

During this replay:

I expire any grants whose expiration time has passed

I add active grants into a min-heap sorted by expiration time

I subtract credits by consuming from the earliest-expiring grants first

If at any point a subtract event has no available credits, then the balance at that timestamp is insufficient and getBalance(ts) throws an exception.
Otherwise, after finishing the replay, the sum of the remaining credits is the balance at time ts

