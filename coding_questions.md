## GPU Credit

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

