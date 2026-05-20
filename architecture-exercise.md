                        ┌────────────────────┐
                        │  Mobile / Web App  │
                        └─────────┬──────────┘
                                  │
                                  ▼
                      ┌──────────────────────┐
                      │ API Gateway / BFF    │
                      │ POST /recommendations│
                      └─────────┬────────────┘
                                │
         ┌──────────────────────┼─────────────────────────┐
         │                      │                         │
         ▼                      ▼                         ▼

┌────────────────┐   ┌──────────────────┐    ┌───────────────────┐
│ User Profile   │   │ Pricing Service  │    │ Recommendation     │
│ Service        │   │ (deterministic)  │    │ Orchestrator       │
│ preferences    │   │ taxes, discounts │    │                    │
└──────┬─────────┘   └──────────────────┘    └─────────┬─────────┘
       │                                                │
       │                                                │
       │                       ┌────────────────────────┼─────────────────────┐
       │                        │                        │                        │
       ▼                        ▼                        ▼                        ▼

┌──────────────┐     ┌────────────────┐    ┌────────────────┐    ┌────────────────┐
│ Redis Cache  │     │ Flight Search  │    │ Hotel Search   │    │ Event Search   │
│ stale data   │     │ Service        │    │ Service        │    │ Service        │
└──────────────┘     │ distributed    │    │ distributed    │    │ distributed    │
                     └────────┬───────┘    └────────┬───────┘    └────────┬───────┘
                              │                     │                     │
                              ▼                     ▼                     ▼

                    ┌──────────────────────────────────────────────┐
                    │ Third-party provider APIs                    │
                    │ different SLAs, timeouts, formats            │
                    └──────────────────────────────────────────────┘


                                ▼
                 ┌────────────────────────────┐
                 │ LLM / MML Ranking Engine   │
                 │ non-deterministic scoring  │
                 │ generates itinerary text   │
                 └────────────┬───────────────┘
                              │
                              ▼
                 ┌────────────────────────────┐
                 │ Safety & Policy Filter     │
                 │ removes unsafe content     │
                 └────────────┬───────────────┘
                              │
                              ▼
                 ┌────────────────────────────┐
                 │ Response Composer          │
                 │ merges all results         │
                 └────────────┬───────────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │ Final JSON Response│
                    └────────────────────┘


## Example response

{
  "tripId": "TRIP-93833",
  "destination": "Tokyo",
  "price": {
    "currency": "EUR",
    "total": 1840.22
  },
  "recommendations": [
    {
      "hotel": "Shinjuku Grand",
      "flight": "AY073",
      "reason": "Great nightlife and short commute."
    }
  ],
  "generatedSummary": "This itinerary balances culture, food, and convenience.",
  "confidenceScore": 0.74,
  "dataFreshness": {
    "flights": "32s",
    "hotels": "5m"
  }
}


## Assignment 1

Task
Your group is the exploratory testing team.
You have:
no complete specs
limited observability
intermittent bugs reported in production:
“prices sometimes wrong”
“recommendations feel random”
“results differ between users”
“timeouts happen during peak traffic”
“unsafe text slipped through once”
Your goal:
Map:
where you would explore first
what risks you suspect
what heuristics or test ideas you would use
what signals would indicate hidden failures

## Analysis example

Hidden Complexity (For Facilitator)
These are not shown initially.
You can reveal them later.
Deterministic Components
- Pricing calculations
- Tax rules
- Currency conversion
- Cache TTL logic
- Authentication
- Response schema

Non-Deterministic Components
- LLM ranking order
- Generated itinerary summary
- Confidence scoring
- Hallucinated reasoning text
- Prompt injection from third-party event descriptions

Distributed System Risks
- Partial failure
- Retry storms
- Eventual consistency
- Stale caches
- Different provider response times
- Duplicate requests
- Timeout races
- Region-specific failures


Things People Commonly Miss
- API Contract Risks
- malformed partial responses
- schema drift
- null handling
- inconsistent enum values

Data Consistency Risks
- hotel and flight from different dates
- stale cache mixed with fresh pricing
- duplicated recommendations
- AI/MML Risks
- non-repeatable results
- unsafe generated text
- hidden bias
- confidence score inconsistency
- explanations not matching actual ranking

Operational Risks
- correlation IDs missing
- impossible debugging
- retries multiplying costs
- silent degradation paths

