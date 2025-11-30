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

# Refactor use event class
from dataclasses import dataclass
from heapq import heappush, heappop

class InsufficientCreditException(Exception):
    pass

@dataclass
class GrantEvent:
    amount: int
    ts: int
    expire_ts: int

@dataclass
class SubtractEvent:
    amount: int
    ts: int


class GpuCreditSystem:
    def __init__(self):
        self.event_log = []

    def createGrant(self, id, amount, ts, expire_ts):
        self.event_log.append(GrantEvent(amount, ts, expire_ts))
    
    def subtract(self, amount, ts):
        self.event_log.append(SubtractEvent(amount, ts))
    
    def getBalance(self, ts):
        # Filter and sort events up to ts
        events = [e for e in self.event_log if e.ts <= ts]
        events.sort(key=lambda e: e.ts)

        active_credits = []  # heap of (expire_ts, remaining_amount)

        def expire_credits(up_to_ts):
            while active_credits and active_credits[0][0] <= up_to_ts:
                heappop(active_credits)

        # Replay events
        for event in events:
            expire_credits(event.ts)

            if isinstance(event, GrantEvent):
                heappush(active_credits, (event.expire_ts, event.amount))

            else:  # SubtractEvent
                need = event.amount
                while need > 0:
                    if not active_credits:
                        raise InsufficientCreditException()

                    expire_ts, available = heappop(active_credits)

                    if available > need:
                        heappush(active_credits, (expire_ts, available - need))
                        need = 0
                    else:
                        need -= available

        expire_credits(ts)
        return sum(amount for _, amount in active_credits)


### Test Cases
import pytest

def test_case_1():
    cs = CreditSystem()

    cs.subtract(1, 30)

    with pytest.raises(InsufficientCreditException):
        cs.getBalance(30)

    with pytest.raises(InsufficientCreditException):
        cs.getBalance(40)

    cs.createGrant("a", 1, 10, 100)

    assert cs.getBalance(10) == 1
    assert cs.getBalance(20) == 1
    assert cs.getBalance(30) == 0

def test_case_2():
    cs = CreditSystem()

    cs.createGrant("a", 3, 10, 60)
    assert cs.getBalance(10) == 3

    cs.createGrant("b", 2, 20, 40)
    cs.subtract(1, 30)
    cs.subtract(3, 50)

    assert cs.getBalance(10) == 3
    assert cs.getBalance(20) == 5
    assert cs.getBalance(30) == 4
    assert cs.getBalance(40) == 3
    assert cs.getBalance(50) == 0

