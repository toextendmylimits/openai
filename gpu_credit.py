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

When a credit reaches its expiration time, is it already expired, or can it still be used at that moment?

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

import heapq

class InsufficientCreditException(Exception):
    pass


class CreditSystem:
    def __init__(self):
        # Store all grant and subtract operations as timestamped events.
        # GRANT:    ("GRANT", amount, ts, exp_ts)
        # SUBTRACT: ("SUBTRACT", amount, ts)
        self.event_log = []

    def createGrant(self, grant_id, amount, ts, exp_ts):
        self.event_log.append(("GRANT", amount, ts, exp_ts))

    def subtract(self, amount, ts):
        self.event_log.append(("SUBTRACT", amount, ts))

    def getBalance(self, ts):
        # 1. Collect all events up to timestamp ts
        eligible_events = [e for e in self.event_log if e[2] <= ts]
        eligible_events.sort(key=lambda e: e[2])  # sort by timestamp

        # Min-heap of active credit buckets (exp_ts, remaining_amount)
        active_credits = []

        def expire_credits(up_to_ts):
            while active_credits and active_credits[0][0] <= up_to_ts:
                heapq.heappop(active_credits)

        # 2. Replay events chronologically
        for event in eligible_events:
            event_type = event[0]
            event_ts = event[2]

            # Expire all grants whose expiration time has passed
            expire_credits(event_ts)

            if event_type == "GRANT":
                _, amount, _, exp_ts = event
                heapq.heappush(active_credits, (exp_ts, amount))

            else:  # SUBTRACT
                _, amount_to_spend, _ = event

                # Spend credits from the earliest-expiring grants first
                while amount_to_spend > 0:
                    if not active_credits:
                        raise InsufficientCreditException()

                    exp_ts, available = heapq.heappop(active_credits)

                    if available > amount_to_spend:
                        # Partially consume this grant
                        leftover = available - amount_to_spend
                        heapq.heappush(active_credits, (exp_ts, leftover))
                        amount_to_spend = 0
                    else:
                        # Fully consume this grant
                        amount_to_spend -= available

        # 3. Expire grants at the end timestamp ts
        expire_credits(ts)

        # 4. Return total remaining credits
        return sum(amount for _, amount in active_credits)


